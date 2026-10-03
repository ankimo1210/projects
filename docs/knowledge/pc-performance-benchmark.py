"""Short synthetic PC benchmarks; use only newly created disposable files."""

import argparse
import concurrent.futures
import ctypes
import hashlib
import json
import mmap
import os
import platform
import statistics
import tempfile
import time
import uuid
import zlib
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_info, threadpool_limits


def summary(name, unit, values, **parameters):
    return {
        "name": name,
        "unit": unit,
        "median": statistics.median(values),
        "samples": values,
        "parameters": parameters,
    }


def cpu(threads):
    results = []
    rng = np.random.default_rng(20261003)
    for dtype in [np.float64, np.float32]:
        n = 2048
        a = rng.standard_normal((n, n)).astype(dtype)
        b = rng.standard_normal((n, n)).astype(dtype)
        c = np.empty_like(a)
        for workers in [1, threads]:
            with threadpool_limits(limits=workers, user_api="blas"):
                np.matmul(a, b, out=c)
                values = []
                for _ in range(5):
                    start = time.perf_counter()
                    np.matmul(a, b, out=c)
                    values.append(2 * n**3 / (time.perf_counter() - start) / 1e9)
            expected = np.dot(a[0].astype(np.float64), b[:, 0].astype(np.float64))
            assert np.isclose(c[0, 0], expected, rtol=1e-3, atol=1e-3)
            results.append(
                summary(
                    f"GEMM_{np.dtype(dtype).name}_{workers}t",
                    "GFLOP/s",
                    values,
                    n=n,
                    threads=workers,
                )
            )
    payload = rng.integers(0, 256, size=8 * 1024 * 1024, dtype=np.uint8).tobytes()
    expected = hashlib.sha256(payload).digest()
    for workers in [1, threads]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for name, operation in [
                ("sha256", lambda _: hashlib.sha256(payload).digest()),
                ("zlib_level6", lambda _: zlib.compress(payload, 6)),
            ]:
                outputs = list(pool.map(operation, range(workers)))
                values = []
                for _ in range(3):
                    start = time.perf_counter()
                    outputs = list(pool.map(operation, range(workers)))
                    values.append(len(payload) * workers / (time.perf_counter() - start) / 1024**2)
                if name == "sha256":
                    assert all(item == expected for item in outputs)
                else:
                    assert zlib.decompress(outputs[0]) == payload
                results.append(
                    summary(f"{name}_{workers}t", "MiB/s", values, payload_MiB=8, threads=workers)
                )
    return results


def memory(threads):
    results = []
    size = 256 * 1024 * 1024
    src = np.full(size // 8, 1.23456789, dtype=np.float64)
    dst = np.empty_like(src)
    for workers in dict.fromkeys([1, 4, 8, threads]):
        chunks = [
            (
                dst[i * len(src) // workers : (i + 1) * len(src) // workers],
                src[i * len(src) // workers : (i + 1) * len(src) // workers],
            )
            for i in range(workers)
        ]

        def copy_chunk(pair):
            for _ in range(5):
                np.copyto(pair[0], pair[1])

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(copy_chunk, chunks))
            values = []
            for _ in range(4):
                start = time.perf_counter()
                list(pool.map(copy_chunk, chunks))
                values.append(2 * size * 5 / (time.perf_counter() - start) / 1e9)
        assert np.all(dst == src)
        results.append(
            summary(
                f"copy_{workers}t",
                "GB/s",
                values,
                array_MiB=256,
                copies=5,
                counted_bytes="read+write",
            )
        )
    del src, dst
    try:
        from numba import njit

        @njit(cache=False)
        def walk(a, index, steps):
            for _ in range(steps):
                index = a[index]
            return index

        nodes = 4 * 1024 * 1024
        order = np.random.default_rng(20261003).permutation(nodes)
        chain = np.empty(nodes * 8, dtype=np.int64)
        chain[order * 8] = np.roll(order, -1) * 8
        first = int(order[0] * 8)
        walk(chain, first, 16)
        assert walk(chain, first, nodes) == first
        values = []
        for _ in range(3):
            start = time.perf_counter()
            assert walk(chain, first, nodes) == first
            values.append((time.perf_counter() - start) * 1e9 / nodes)
        results.append(
            summary(
                "dependent_pointer_chase",
                "ns/load",
                values,
                footprint_MiB=256,
                cache_line_stride=64,
                loads=nodes,
            )
        )
    except ImportError:
        results.append(
            {
                "name": "dependent_pointer_chase",
                "status": "unavailable",
                "reason": "numba is not installed",
            }
        )
    return results


def gpu():
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA device is unavailable")
    torch.manual_seed(20261003)
    results = []

    def measure(operation, work, unit, loops, **parameters):
        for _ in range(3):
            operation()
        torch.cuda.synchronize()
        values = []
        for _ in range(5):
            start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
            start.record()
            for _ in range(loops):
                operation()
            end.record()
            end.synchronize()
            seconds = start.elapsed_time(end) / 1000
            assert seconds > 0
            values.append(work * loops / seconds)
        return summary(parameters.pop("name"), unit, values, loops=loops, **parameters)

    torch.backends.fp32_precision = "ieee"
    torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = False
    torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction = False
    for name, dtype, precision, n in [
        ("FP32_IEEE", torch.float32, "ieee", 4096),
        ("TF32", torch.float32, "tf32", 8192),
        ("FP16", torch.float16, "ieee", 8192),
        ("BF16", torch.bfloat16, "ieee", 8192),
    ]:
        torch.backends.cuda.matmul.fp32_precision = precision
        a = torch.randn((n, n), device="cuda", dtype=dtype)
        b = torch.randn_like(a)
        c = torch.empty_like(a)
        result = measure(
            lambda a=a, b=b, c=c: torch.mm(a, b, out=c),
            2 * n**3 / 1e12,
            "TFLOP/s",
            10,
            name=name,
            n=n,
            precision=precision,
        )
        expected = (a[0].double() * b[:, 0].double()).sum().item()
        actual = c[0, 0].item()
        tolerance = 0.03 if dtype == torch.bfloat16 else 0.003
        assert abs(actual - expected) <= tolerance * max(1, abs(expected)), (name, actual, expected)
        result["relative_error_one_element"] = abs(actual - expected) / max(1, abs(expected))
        results.append(result)
        del a, b, c
    size = 1024**3
    a = torch.rand(size // 4, device="cuda")
    b = torch.empty_like(a)
    results.append(
        measure(
            lambda a=a, b=b: b.copy_(a),
            2 * size / 1e9,
            "GB/s",
            20,
            name="VRAM_copy",
            array_MiB=1024,
            counted_bytes="read+write",
        )
    )
    assert torch.equal(a[:1024], b[:1024])
    del a, b
    size = 128 * 1024**2
    host = torch.randn(size // 4, pin_memory=True)
    dest_host = torch.empty_like(host, pin_memory=True)
    device = torch.empty(size // 4, device="cuda")
    results.append(
        measure(
            lambda: device.copy_(host, non_blocking=True),
            size / 1e9,
            "GB/s",
            10,
            name="pinned_H2D",
            buffer_MiB=128,
        )
    )
    results.append(
        measure(
            lambda: dest_host.copy_(device, non_blocking=True),
            size / 1e9,
            "GB/s",
            10,
            name="pinned_D2H",
            buffer_MiB=128,
        )
    )
    assert torch.equal(host[:1024], dest_host[:1024])
    return {
        "torch": torch.__version__,
        "runtime_cuda": torch.version.cuda,
        "device": torch.cuda.get_device_name(),
        "compute_capability": torch.cuda.get_device_capability(),
        "results": results,
    }


class DirectFile:
    def __init__(self, path, block):
        self.path, self.block = path, block
        self.created = False
        self.handle = None
        self.buf = None
        if os.name == "nt":
            from ctypes import wintypes as wt

            k = self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            k.CreateFileW.argtypes = [
                wt.LPCWSTR,
                wt.DWORD,
                wt.DWORD,
                ctypes.c_void_p,
                wt.DWORD,
                wt.DWORD,
                wt.HANDLE,
            ]
            k.CreateFileW.restype = wt.HANDLE
            k.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
            k.VirtualAlloc.restype = ctypes.c_void_p
            k.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wt.DWORD]
            for name in ["ReadFile", "WriteFile"]:
                getattr(k, name).argtypes = [
                    wt.HANDLE,
                    ctypes.c_void_p,
                    wt.DWORD,
                    ctypes.POINTER(wt.DWORD),
                    ctypes.c_void_p,
                ]
            k.SetFilePointerEx.argtypes = [wt.HANDLE, ctypes.c_longlong, ctypes.c_void_p, wt.DWORD]
            k.FlushFileBuffers.argtypes = [wt.HANDLE]
            k.CloseHandle.argtypes = [wt.HANDLE]
            self.handle = k.CreateFileW(str(path), 0xC0000000, 0, None, 1, 0xA0000000, None)
            if self.handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            self.created = True
            self.buf = k.VirtualAlloc(None, block, 0x3000, 0x04)
            if not self.buf:
                self.close()
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            self.handle = os.open(
                path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_DIRECT | os.O_DSYNC, 0o600
            )
            self.created = True
            self.buf = mmap.mmap(-1, block)

    def load(self, data):
        if os.name == "nt":
            ctypes.memmove(self.buf, data, len(data))
        else:
            self.buf[: len(data)] = data

    def bytes(self, length):
        return ctypes.string_at(self.buf, length) if os.name == "nt" else self.buf[:length]

    def io(self, write, offset, size):
        if os.name == "nt":
            count = ctypes.c_ulong()
            if not self.kernel.SetFilePointerEx(self.handle, offset, None, 0):
                raise ctypes.WinError(ctypes.get_last_error())
            operation = self.kernel.WriteFile if write else self.kernel.ReadFile
            if not operation(self.handle, self.buf, size, ctypes.byref(count), None):
                raise ctypes.WinError(ctypes.get_last_error())
            assert count.value == size
        else:
            view = memoryview(self.buf)[:size]
            try:
                count = (
                    os.pwrite(self.handle, view, offset)
                    if write
                    else os.preadv(self.handle, [view], offset)
                )
                assert count == size
            finally:
                view.release()

    def flush(self):
        if os.name == "nt":
            if not self.kernel.FlushFileBuffers(self.handle):
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            os.fsync(self.handle)

    def close(self):
        if self.handle is not None:
            if os.name == "nt":
                self.kernel.CloseHandle(self.handle)
                if self.buf:
                    self.kernel.VirtualFree(self.buf, 0, 0x8000)
            else:
                os.close(self.handle)
                if self.buf is not None:
                    self.buf.close()
            self.handle = None
        if self.created:
            self.path.unlink()
            self.created = False


def storage(directory):
    directory = Path(directory).resolve(strict=True)
    path = directory / f"pc-performance-{uuid.uuid4().hex}.bin"
    size, block = 1024**3, 8 * 1024**2
    pattern = np.random.default_rng(20261003).integers(0, 256, size=block, dtype=np.uint8).tobytes()
    direct = DirectFile(path, block)
    results = []
    try:
        direct.load(pattern)
        for write in [True, False]:
            values = []
            for _ in range(3):
                start = time.perf_counter()
                for offset in range(0, size, block):
                    direct.io(write, offset, block)
                if write:
                    direct.flush()
                values.append(size / (time.perf_counter() - start) / 1e6)
            if not write:
                assert direct.bytes(4096) == pattern[:4096]
            results.append(
                summary(
                    "sequential_write" if write else "sequential_read",
                    "MB/s",
                    values,
                    file_MiB=1024,
                    block_MiB=8,
                    queue_depth=1,
                    direct_io=True,
                    durable_write=True,
                )
            )
        rng = np.random.default_rng(20261003)
        values = []
        for _ in range(3):
            offsets = rng.integers(0, size // 4096, size=2048) * 4096
            start = time.perf_counter()
            for offset in offsets:
                direct.io(False, int(offset), 4096)
            elapsed = time.perf_counter() - start
            values.append(len(offsets) / elapsed)
            final = int(offsets[-1]) % block
            assert direct.bytes(4096) == pattern[final : final + 4096]
        results.append(
            summary(
                "random_read_4KiB_QD1",
                "IOPS",
                values,
                reads=2048,
                file_MiB=1024,
                queue_depth=1,
                direct_io=True,
            )
        )
    finally:
        direct.close()
    assert not path.exists()
    return {"results": results, "temporary_file_removed": True, "write_volume_GiB": 3}


def filesystem(directory):
    directory = Path(directory).resolve(strict=True)
    folder = Path(tempfile.mkdtemp(prefix="pc-performance-", dir=directory))
    paths = [folder / f"{index:04d}.bin" for index in range(200)]
    results = []
    try:
        payload = bytes(1024)
        start = time.perf_counter()
        for path in paths:
            with path.open("xb") as f:
                f.write(payload)
        results.append(
            summary(
                "create_small_files",
                "files/s",
                [len(paths) / (time.perf_counter() - start)],
                files=200,
                bytes_each=1024,
                fsync=False,
            )
        )
        values = []
        for _ in range(5):
            start = time.perf_counter()
            assert sum(path.stat().st_size for path in paths) == 200 * 1024
            values.append(len(paths) / (time.perf_counter() - start))
        results.append(summary("stat_warm", "files/s", values, files=200, warm_cache=True))
    finally:
        for path in paths:
            if path.exists():
                path.unlink()
        folder.rmdir()
    return {"results": results, "temporary_files_removed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("section", choices=["cpu", "memory", "gpu", "storage", "filesystem"])
    parser.add_argument("--threads", type=int, default=os.cpu_count())
    parser.add_argument("--directory", default=tempfile.gettempdir())
    parser.add_argument(
        "--label", required=True, help="Public, generic environment label; no account or host name"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.threads <= (os.cpu_count() or 1):
        parser.error("threads must be within the available logical CPU count")
    result = {
        "schema_version": 1,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "label": args.label,
        "section": args.section,
        "environment": {
            "os": platform.system(),
            "kernel": platform.release(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "logical_cpus": os.cpu_count(),
            "blas": [
                {
                    key: value
                    for key, value in item.items()
                    if key in ["internal_api", "version", "num_threads", "architecture"]
                }
                for item in threadpool_info()
            ],
        },
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    start = time.perf_counter()
    try:
        if args.section == "cpu":
            result["measurement"] = cpu(args.threads)
        elif args.section == "memory":
            result["measurement"] = memory(args.threads)
        elif args.section == "gpu":
            result["measurement"] = gpu()
        elif args.section == "storage":
            result["measurement"] = storage(args.directory)
        else:
            result["measurement"] = filesystem(args.directory)
        result["status"] = "ok"
    except Exception as exc:
        result["status"] = "error"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        raise
    finally:
        result["wall_seconds"] = time.perf_counter() - start
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "label": args.label,
                    "section": args.section,
                    "status": result["status"],
                    "wall_seconds": result["wall_seconds"],
                }
            )
        )


if __name__ == "__main__":
    main()
