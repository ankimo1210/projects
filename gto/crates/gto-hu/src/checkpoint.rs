//! Durable, dependency-free solver checkpoints for long P0a runs.
//!
//! The immutable solver configuration is rebuilt by the caller and matched
//! by a stable fingerprint before mutable state is applied. Payloads are
//! streamed directly to disk and verified in a dry pass before restoration,
//! avoiding a second in-memory copy of multi-gigabyte CFR tables.

use std::collections::HashSet;
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::OnceLock;
use std::time::{Duration, Instant};

const MAGIC: &[u8; 8] = b"GTOCKP1\0";
const SCHEMA_VERSION: u32 = 1;
const ENDIAN_MARKER: u32 = 0x0102_0304;
const FOOTER_BYTES: u64 = 16;
const MAX_BUILD_ID_BYTES: usize = 4096;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum SolverKind {
    Flop = 1,
    Blueprint = 2,
}

impl SolverKind {
    fn from_byte(value: u8) -> io::Result<Self> {
        match value {
            1 => Ok(Self::Flop),
            2 => Ok(Self::Blueprint),
            _ => Err(invalid_data(format!("unknown solver kind {value}"))),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct CheckpointInfo {
    pub path: PathBuf,
    pub iteration: u32,
    pub payload_bytes: u64,
    pub bytes: u64,
    pub checksum: u64,
    pub io_s: f64,
}

/// Wall/iteration trigger evaluated only between complete CFR iterations.
pub struct CheckpointTrigger {
    every: Duration,
    every_iters: Option<u32>,
    last_iteration: u32,
    last_save: Instant,
}

impl CheckpointTrigger {
    pub fn new(every_minutes: u64, every_iters: Option<u32>, iteration: u32) -> Self {
        Self {
            every: Duration::from_secs(every_minutes.saturating_mul(60)),
            every_iters: every_iters.filter(|&value| value > 0),
            last_iteration: iteration,
            last_save: Instant::now(),
        }
    }

    pub fn due(&self, iteration: u32) -> bool {
        let iteration_due = self
            .every_iters
            .is_some_and(|interval| iteration.saturating_sub(self.last_iteration) >= interval);
        let wall_due = !self.every.is_zero() && self.last_save.elapsed() >= self.every;
        iteration_due || wall_due
    }

    pub fn mark_saved(&mut self, iteration: u32) {
        self.last_iteration = iteration;
        self.last_save = Instant::now();
    }
}

#[derive(Debug)]
struct Header {
    kind: SolverKind,
    build_id: String,
    config_fingerprint: u64,
    iteration: u32,
    payload_bytes: u64,
}

#[derive(Clone, Copy)]
pub(crate) struct ExpectedCheckpoint<'a> {
    pub kind: SolverKind,
    pub build_id: &'a str,
    pub config_fingerprint: u64,
}

fn invalid_data(message: impl Into<String>) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message.into())
}

fn invalid_input(message: impl Into<String>) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidInput, message.into())
}

fn crc64_table() -> &'static [u64; 256] {
    static TABLE: OnceLock<[u64; 256]> = OnceLock::new();
    TABLE.get_or_init(|| {
        const POLY: u64 = 0x42F0_E1EB_A9EA_3693;
        let mut table = [0u64; 256];
        for (index, slot) in table.iter_mut().enumerate() {
            let mut crc = (index as u64) << 56;
            for _ in 0..8 {
                crc = if crc & (1 << 63) != 0 {
                    (crc << 1) ^ POLY
                } else {
                    crc << 1
                };
            }
            *slot = crc;
        }
        table
    })
}

#[derive(Default)]
struct Crc64(u64);

impl Crc64 {
    fn update(&mut self, bytes: &[u8]) {
        let table = crc64_table();
        for &byte in bytes {
            let index = ((self.0 >> 56) as u8 ^ byte) as usize;
            self.0 = table[index] ^ (self.0 << 8);
        }
    }

    fn finish(&self) -> u64 {
        self.0
    }
}

struct CrcWriter<W> {
    inner: W,
    crc: Crc64,
    bytes: u64,
}

impl<W> CrcWriter<W> {
    fn new(inner: W) -> Self {
        Self {
            inner,
            crc: Crc64::default(),
            bytes: 0,
        }
    }

    fn checksum(&self) -> u64 {
        self.crc.finish()
    }

    fn into_inner(self) -> W {
        self.inner
    }
}

impl<W: Write> Write for CrcWriter<W> {
    fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
        let written = self.inner.write(buffer)?;
        self.crc.update(&buffer[..written]);
        self.bytes = self
            .bytes
            .checked_add(written as u64)
            .ok_or_else(|| invalid_data("checkpoint byte counter overflow"))?;
        Ok(written)
    }

    fn flush(&mut self) -> io::Result<()> {
        self.inner.flush()
    }
}

struct CrcReader<R> {
    inner: R,
    crc: Crc64,
    bytes: u64,
}

impl<R> CrcReader<R> {
    fn new(inner: R) -> Self {
        Self {
            inner,
            crc: Crc64::default(),
            bytes: 0,
        }
    }

    fn checksum(&self) -> u64 {
        self.crc.finish()
    }

    fn into_inner(self) -> R {
        self.inner
    }
}

impl<R: Read> Read for CrcReader<R> {
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        let read = self.inner.read(buffer)?;
        self.crc.update(&buffer[..read]);
        self.bytes = self
            .bytes
            .checked_add(read as u64)
            .ok_or_else(|| invalid_data("checkpoint byte counter overflow"))?;
        Ok(read)
    }
}

pub(crate) struct PayloadWriter<'a> {
    inner: &'a mut dyn Write,
    bytes: u64,
}

impl<'a> PayloadWriter<'a> {
    fn new(inner: &'a mut dyn Write) -> Self {
        Self { inner, bytes: 0 }
    }

    fn write_all(&mut self, bytes: &[u8]) -> io::Result<()> {
        self.inner.write_all(bytes)?;
        self.bytes = self
            .bytes
            .checked_add(bytes.len() as u64)
            .ok_or_else(|| invalid_data("payload byte counter overflow"))?;
        Ok(())
    }

    pub(crate) fn bytes_written(&self) -> u64 {
        self.bytes
    }

    pub(crate) fn write_u8(&mut self, value: u8) -> io::Result<()> {
        self.write_all(&[value])
    }

    pub(crate) fn write_u32(&mut self, value: u32) -> io::Result<()> {
        self.write_all(&value.to_le_bytes())
    }

    pub(crate) fn write_u64(&mut self, value: u64) -> io::Result<()> {
        self.write_all(&value.to_le_bytes())
    }

    pub(crate) fn write_f64(&mut self, value: f64) -> io::Result<()> {
        self.write_u64(value.to_bits())
    }
}

pub(crate) struct PayloadReader<'a> {
    inner: &'a mut dyn Read,
    bytes: u64,
}

impl<'a> PayloadReader<'a> {
    fn new(inner: &'a mut dyn Read) -> Self {
        Self { inner, bytes: 0 }
    }

    fn read_exact(&mut self, bytes: &mut [u8]) -> io::Result<()> {
        self.inner.read_exact(bytes)?;
        self.bytes = self
            .bytes
            .checked_add(bytes.len() as u64)
            .ok_or_else(|| invalid_data("payload byte counter overflow"))?;
        Ok(())
    }

    pub(crate) fn bytes_read(&self) -> u64 {
        self.bytes
    }

    pub(crate) fn read_u8(&mut self) -> io::Result<u8> {
        let mut bytes = [0u8; 1];
        self.read_exact(&mut bytes)?;
        Ok(bytes[0])
    }

    pub(crate) fn read_u32(&mut self) -> io::Result<u32> {
        let mut bytes = [0u8; 4];
        self.read_exact(&mut bytes)?;
        Ok(u32::from_le_bytes(bytes))
    }

    pub(crate) fn read_u64(&mut self) -> io::Result<u64> {
        let mut bytes = [0u8; 8];
        self.read_exact(&mut bytes)?;
        Ok(u64::from_le_bytes(bytes))
    }

    pub(crate) fn read_f64(&mut self) -> io::Result<f64> {
        Ok(f64::from_bits(self.read_u64()?))
    }

    pub(crate) fn skip_bytes(&mut self, mut remaining: u64) -> io::Result<()> {
        let mut buffer = [0u8; 8192];
        while remaining > 0 {
            let amount = usize::try_from(remaining.min(buffer.len() as u64)).unwrap();
            self.read_exact(&mut buffer[..amount])?;
            remaining -= amount as u64;
        }
        Ok(())
    }

    pub(crate) fn drain(&mut self) -> io::Result<()> {
        let mut buffer = [0u8; 8192];
        loop {
            let read = self.inner.read(&mut buffer)?;
            if read == 0 {
                return Ok(());
            }
            self.bytes = self
                .bytes
                .checked_add(read as u64)
                .ok_or_else(|| invalid_data("payload byte counter overflow"))?;
        }
    }
}

/// Stable dependency-free hash used for immutable configuration fingerprints
/// and mutable-state test checksums. This is accidental mismatch detection,
/// not a cryptographic boundary.
pub(crate) struct StableHasher(Crc64);

impl StableHasher {
    pub(crate) fn new(domain: &[u8]) -> Self {
        let mut crc = Crc64::default();
        crc.update(domain);
        Self(crc)
    }

    pub(crate) fn update(&mut self, bytes: &[u8]) {
        self.0.update(bytes);
    }

    pub(crate) fn write_u8(&mut self, value: u8) {
        self.update(&[value]);
    }

    pub(crate) fn write_u32(&mut self, value: u32) {
        self.update(&value.to_le_bytes());
    }

    pub(crate) fn write_u64(&mut self, value: u64) {
        self.update(&value.to_le_bytes());
    }

    pub(crate) fn write_f64(&mut self, value: f64) {
        self.write_u64(value.to_bits());
    }

    pub(crate) fn finish(&self) -> u64 {
        self.0.finish()
    }
}

fn write_header(writer: &mut dyn Write, header: &Header) -> io::Result<()> {
    let build_id = header.build_id.as_bytes();
    if build_id.len() > MAX_BUILD_ID_BYTES {
        return Err(invalid_input(format!(
            "build id is too long: {} bytes (max {MAX_BUILD_ID_BYTES})",
            build_id.len()
        )));
    }
    writer.write_all(MAGIC)?;
    writer.write_all(&SCHEMA_VERSION.to_le_bytes())?;
    writer.write_all(&[header.kind as u8])?;
    writer.write_all(&ENDIAN_MARKER.to_le_bytes())?;
    writer.write_all(&(build_id.len() as u32).to_le_bytes())?;
    writer.write_all(&header.config_fingerprint.to_le_bytes())?;
    writer.write_all(&header.iteration.to_le_bytes())?;
    writer.write_all(&header.payload_bytes.to_le_bytes())?;
    writer.write_all(build_id)
}

fn read_exact_array<const N: usize>(reader: &mut dyn Read) -> io::Result<[u8; N]> {
    let mut bytes = [0u8; N];
    reader.read_exact(&mut bytes)?;
    Ok(bytes)
}

fn read_header(reader: &mut dyn Read) -> io::Result<Header> {
    if &read_exact_array::<8>(reader)? != MAGIC {
        return Err(invalid_data("checkpoint magic mismatch"));
    }
    let schema = u32::from_le_bytes(read_exact_array(reader)?);
    if schema != SCHEMA_VERSION {
        return Err(invalid_data(format!(
            "checkpoint schema mismatch: expected {SCHEMA_VERSION}, got {schema}"
        )));
    }
    let kind = SolverKind::from_byte(read_exact_array::<1>(reader)?[0])?;
    let endian = u32::from_le_bytes(read_exact_array(reader)?);
    if endian != ENDIAN_MARKER {
        return Err(invalid_data("checkpoint endianness marker mismatch"));
    }
    let build_len = u32::from_le_bytes(read_exact_array(reader)?) as usize;
    if build_len > MAX_BUILD_ID_BYTES {
        return Err(invalid_data(format!(
            "checkpoint build id length {build_len} exceeds {MAX_BUILD_ID_BYTES}"
        )));
    }
    let config_fingerprint = u64::from_le_bytes(read_exact_array(reader)?);
    let iteration = u32::from_le_bytes(read_exact_array(reader)?);
    let payload_bytes = u64::from_le_bytes(read_exact_array(reader)?);
    let mut build_id = vec![0u8; build_len];
    reader.read_exact(&mut build_id)?;
    let build_id = String::from_utf8(build_id)
        .map_err(|_| invalid_data("checkpoint build id is not valid UTF-8"))?;
    Ok(Header {
        kind,
        build_id,
        config_fingerprint,
        iteration,
        payload_bytes,
    })
}

fn validate_header(header: &Header, expected: ExpectedCheckpoint<'_>) -> io::Result<()> {
    if header.kind != expected.kind {
        return Err(invalid_data(format!(
            "solver kind mismatch: expected {:?}, got {:?}",
            expected.kind, header.kind
        )));
    }
    if header.build_id != expected.build_id {
        return Err(invalid_data(format!(
            "checkpoint build id mismatch: expected {:?}, got {:?}",
            expected.build_id, header.build_id
        )));
    }
    if header.config_fingerprint != expected.config_fingerprint {
        return Err(invalid_data(format!(
            "configuration fingerprint mismatch: expected {:016x}, got {:016x}",
            expected.config_fingerprint, header.config_fingerprint
        )));
    }
    Ok(())
}

pub(crate) fn read_checkpoint<T>(
    path: &Path,
    expected: ExpectedCheckpoint<'_>,
    read_payload: impl FnOnce(&mut PayloadReader<'_>) -> io::Result<T>,
) -> io::Result<(CheckpointInfo, T)> {
    let started = Instant::now();
    let file = File::open(path)?;
    let file_bytes = file.metadata()?.len();
    if file_bytes < MAGIC.len() as u64 + FOOTER_BYTES {
        return Err(invalid_data(format!(
            "checkpoint is truncated: {file_bytes} bytes"
        )));
    }

    let mut reader = CrcReader::new(BufReader::new(file));
    let header = read_header(&mut reader)?;
    validate_header(&header, expected)?;
    let body_bytes = reader
        .bytes
        .checked_add(header.payload_bytes)
        .ok_or_else(|| invalid_data("checkpoint length overflow"))?;
    let expected_file_bytes = body_bytes
        .checked_add(FOOTER_BYTES)
        .ok_or_else(|| invalid_data("checkpoint length overflow"))?;
    if expected_file_bytes != file_bytes {
        return Err(invalid_data(format!(
            "checkpoint length mismatch: header implies {expected_file_bytes} bytes, file has {file_bytes}"
        )));
    }

    let value = {
        let mut limited = (&mut reader).take(header.payload_bytes);
        let mut payload = PayloadReader::new(&mut limited);
        let value = read_payload(&mut payload)?;
        if payload.bytes_read() != header.payload_bytes {
            return Err(invalid_data(format!(
                "payload reader consumed {} of {} bytes",
                payload.bytes_read(),
                header.payload_bytes
            )));
        }
        value
    };
    if reader.bytes != body_bytes {
        return Err(invalid_data("checkpoint payload did not end at footer"));
    }
    let checksum = reader.checksum();
    let mut inner = reader.into_inner();
    let repeated_payload_bytes = u64::from_le_bytes(read_exact_array(&mut inner)?);
    let stored_checksum = u64::from_le_bytes(read_exact_array(&mut inner)?);
    if repeated_payload_bytes != header.payload_bytes {
        return Err(invalid_data(format!(
            "checkpoint footer length mismatch: expected {}, got {repeated_payload_bytes}",
            header.payload_bytes
        )));
    }
    if stored_checksum != checksum {
        return Err(invalid_data(format!(
            "checkpoint CRC64 mismatch: expected {stored_checksum:016x}, got {checksum:016x}"
        )));
    }

    Ok((
        CheckpointInfo {
            path: path.to_path_buf(),
            iteration: header.iteration,
            payload_bytes: header.payload_bytes,
            bytes: file_bytes,
            checksum,
            io_s: started.elapsed().as_secs_f64(),
        },
        value,
    ))
}

fn atomic_write(path: &Path, temp_path: &Path, bytes: &[u8]) -> io::Result<()> {
    let file = OpenOptions::new()
        .create(true)
        .truncate(true)
        .write(true)
        .open(temp_path)?;
    let mut writer = BufWriter::new(file);
    writer.write_all(bytes)?;
    writer.flush()?;
    writer.get_ref().sync_all()?;
    fs::rename(temp_path, path)
}

/// Atomically refresh the small benchmark sidecar paired with a committed
/// numbered solver generation.
pub fn replace_companion(checkpoint_path: &Path, bytes: &[u8]) -> io::Result<()> {
    let dir = checkpoint_path.parent().ok_or_else(|| {
        invalid_input(format!(
            "checkpoint has no parent directory: {}",
            checkpoint_path.display()
        ))
    })?;
    atomic_write(
        &checkpoint_path.with_extension("bench"),
        &dir.join("checkpoint.bench.tmp"),
        bytes,
    )?;
    sync_directory(dir)
}

#[cfg(unix)]
fn sync_directory(path: &Path) -> io::Result<()> {
    File::open(path)?.sync_all()
}

#[cfg(not(unix))]
fn sync_directory(_path: &Path) -> io::Result<()> {
    Ok(())
}

fn generation_name(iteration: u32) -> String {
    format!("checkpoint-{iteration:012}.bin")
}

fn generation_iteration(path: &Path) -> Option<u32> {
    let name = path.file_name()?.to_str()?;
    let digits = name.strip_prefix("checkpoint-")?.strip_suffix(".bin")?;
    (digits.len() == 12).then_some(())?;
    digits.parse().ok()
}

fn numbered_generations(dir: &Path) -> io::Result<Vec<PathBuf>> {
    let mut generations = Vec::new();
    for entry in fs::read_dir(dir)? {
        let path = entry?.path();
        if generation_iteration(&path).is_some() {
            generations.push(path);
        }
    }
    generations.sort_by_key(|path| std::cmp::Reverse(generation_iteration(path).unwrap()));
    Ok(generations)
}

fn prune_generations(
    dir: &Path,
    keep: usize,
    current_path: &Path,
    expected: ExpectedCheckpoint<'_>,
) -> io::Result<()> {
    let generations = numbered_generations(dir)?;
    let mut retained = HashSet::new();
    retained.insert(current_path.to_path_buf());
    for path in &generations {
        if retained.len() >= keep {
            break;
        }
        if path == current_path {
            continue;
        }
        if read_checkpoint(path, expected, |reader| reader.drain()).is_ok() {
            retained.insert(path.clone());
        }
    }
    for path in generations {
        if retained.contains(&path) {
            continue;
        }
        fs::remove_file(&path)?;
        let companion = path.with_extension("bench");
        if companion.exists() {
            fs::remove_file(companion)?;
        }
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn write_checkpoint(
    dir: &Path,
    kind: SolverKind,
    build_id: &str,
    config_fingerprint: u64,
    iteration: u32,
    payload_bytes: u64,
    keep: usize,
    companion: Option<&[u8]>,
    write_payload: impl FnOnce(&mut PayloadWriter<'_>) -> io::Result<()>,
) -> io::Result<CheckpointInfo> {
    if keep < 2 {
        return Err(invalid_input("keep_checkpoints must be at least 2"));
    }
    fs::create_dir_all(dir)?;
    let started = Instant::now();
    let temp_path = dir.join("checkpoint.tmp");
    let name = generation_name(iteration);
    let final_path = dir.join(&name);
    let header = Header {
        kind,
        build_id: build_id.to_string(),
        config_fingerprint,
        iteration,
        payload_bytes,
    };

    let file = OpenOptions::new()
        .create(true)
        .truncate(true)
        .write(true)
        .open(&temp_path)?;
    let mut writer = CrcWriter::new(BufWriter::new(file));
    write_header(&mut writer, &header)?;
    {
        let mut payload = PayloadWriter::new(&mut writer);
        write_payload(&mut payload)?;
        if payload.bytes_written() != payload_bytes {
            return Err(invalid_data(format!(
                "checkpoint payload length mismatch while writing: expected {payload_bytes}, wrote {}",
                payload.bytes_written()
            )));
        }
    }
    writer.flush()?;
    let checksum = writer.checksum();
    let mut writer = writer.into_inner();
    writer.write_all(&payload_bytes.to_le_bytes())?;
    writer.write_all(&checksum.to_le_bytes())?;
    writer.flush()?;
    writer.get_ref().sync_all()?;
    drop(writer);
    fs::rename(&temp_path, &final_path)?;

    if let Some(bytes) = companion {
        atomic_write(
            &final_path.with_extension("bench"),
            &dir.join("checkpoint.bench.tmp"),
            bytes,
        )?;
    } else {
        let stale_companion = final_path.with_extension("bench");
        if stale_companion.exists() {
            fs::remove_file(stale_companion)?;
        }
    }

    atomic_write(
        &dir.join("LATEST"),
        &dir.join("LATEST.tmp"),
        format!("{name}\n").as_bytes(),
    )?;
    sync_directory(dir)?;
    prune_generations(
        dir,
        keep,
        &final_path,
        ExpectedCheckpoint {
            kind,
            build_id,
            config_fingerprint,
        },
    )?;
    sync_directory(dir)?;

    let bytes = fs::metadata(&final_path)?.len();
    Ok(CheckpointInfo {
        path: final_path,
        iteration,
        payload_bytes,
        bytes,
        checksum,
        io_s: started.elapsed().as_secs_f64(),
    })
}

/// Ordered recovery candidates: `LATEST` first, then numbered generations
/// newest-to-oldest. Callers validate each candidate before applying state.
pub fn recovery_candidates(dir: &Path) -> io::Result<Vec<PathBuf>> {
    if !dir.is_dir() {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            format!("checkpoint directory does not exist: {}", dir.display()),
        ));
    }
    let mut candidates = Vec::new();
    let latest_path = dir.join("LATEST");
    if let Ok(contents) = fs::read_to_string(&latest_path) {
        let name = contents.trim();
        let candidate_name = Path::new(name);
        if !name.is_empty()
            && candidate_name.file_name().is_some_and(|file| file == name)
            && generation_iteration(candidate_name).is_some()
        {
            candidates.push(dir.join(candidate_name));
        }
    }
    candidates.extend(numbered_generations(dir)?);

    let mut seen = HashSet::new();
    candidates.retain(|path| seen.insert(path.clone()));
    if candidates.is_empty() {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            format!("no checkpoint generations found in {}", dir.display()),
        ));
    }
    Ok(candidates)
}

/// Best-effort exact source build identifier for CLI-created checkpoints.
/// CI/release builds can pin it at compile time with `GTO_BUILD_ID`.
pub fn current_build_id() -> String {
    if let Some(build_id) = option_env!("GTO_BUILD_ID") {
        return build_id.to_string();
    }
    let output = Command::new("git")
        .arg("-C")
        .arg(env!("CARGO_MANIFEST_DIR"))
        .args(["rev-parse", "HEAD"])
        .output();
    match output {
        Ok(output) if output.status.success() => {
            String::from_utf8_lossy(&output.stdout).trim().to_string()
        }
        _ => format!("gto-hu-{}", env!("CARGO_PKG_VERSION")),
    }
}
