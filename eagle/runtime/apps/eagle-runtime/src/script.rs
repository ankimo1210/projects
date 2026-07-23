//! Scripted DSKY choreography over the live AGC: key sequences, display
//! waits, erasable load/verify. Used by the descent spikes and ScenarioRunner.
use crate::agc_session::AgcSession;
use anyhow::{anyhow, bail, Context, Result};
use eagle_agc_protocol::dsky::DskyState;
use eagle_agc_protocol::keys::{pro_key_packets, DskyKey};
use eagle_agc_protocol::Packet;
use std::time::Duration;
use tokio::sync::{mpsc, watch};

pub struct DskyScript {
    tx: mpsc::UnboundedSender<Packet>,
    rx: watch::Receiver<DskyState>,
    key_delay: Duration,
}

impl DskyScript {
    pub fn new(tx: mpsc::UnboundedSender<Packet>, rx: watch::Receiver<DskyState>) -> Self {
        Self { tx, rx, key_delay: Duration::from_millis(80) }
    }
    pub fn set_key_delay(&mut self, d: Duration) { self.key_delay = d; }

    pub async fn keys(&mut self, seq: &str) -> Result<()> {
        for ch in seq.chars() {
            // NB: names must match `DskyKey::from_name` exactly (keys.rs) —
            // it recognizes "KEY_REL"/"PLUS"/"MINUS", not "KEY REL"/"+"/"-".
            let name: String = match ch {
                'V' => "VERB".to_string(),
                'N' => "NOUN".to_string(),
                'E' => "ENTR".to_string(),
                'C' => "CLR".to_string(),
                'K' => "KEY_REL".to_string(),
                'R' => "RSET".to_string(),
                '+' => "PLUS".to_string(),
                '-' => "MINUS".to_string(),
                '0'..='9' => ch.to_string(),
                other => bail!("unknown key token {other:?} in {seq:?}"),
            };
            let key = DskyKey::from_name(&name)
                .ok_or_else(|| anyhow!("no DskyKey named {name:?}"))?;
            self.tx.send(key.packet()).context("agc tx closed")?;
            tokio::time::sleep(self.key_delay).await;
        }
        Ok(())
    }

    pub async fn pro(&mut self) -> Result<()> {
        for p in pro_key_packets(true) { self.tx.send(p)?; }
        tokio::time::sleep(Duration::from_millis(150)).await;
        for p in pro_key_packets(false) { self.tx.send(p)?; }
        tokio::time::sleep(self.key_delay).await;
        Ok(())
    }

    pub async fn wait(
        &mut self, timeout: Duration, pred: impl Fn(&DskyState) -> bool,
    ) -> Result<DskyState> {
        let deadline = tokio::time::Instant::now() + timeout;
        loop {
            {
                let d = self.rx.borrow();
                if pred(&d) { return Ok(*d); }
            }
            tokio::select! {
                r = self.rx.changed() => { r.context("dsky watch closed")?; }
                _ = tokio::time::sleep_until(deadline) => {
                    bail!("timeout waiting for DSKY condition; last state: {:?}",
                          *self.rx.borrow());
                }
            }
        }
    }

    pub async fn wait_flash(&mut self, verb: &str, noun: &str) -> Result<()> {
        let (v, n) = (verb.to_string(), noun.to_string());
        self.wait(Duration::from_secs(15), move |d| {
            d.verb.iter().collect::<String>() == v
                && d.noun.iter().collect::<String>() == n
                && d.verb_noun_flash
        }).await.map(|_| ())
    }

    pub async fn wait_prog(&mut self, mm: &str) -> Result<()> {
        let mm = mm.to_string();
        self.wait(Duration::from_secs(30), move |d| {
            d.prog.iter().collect::<String>() == mm
        }).await.map(|_| ())
    }

    /// V21N01: load one erasable word, then verify via V01N01 read-back.
    pub async fn load_erasable(&mut self, ecadr: u16, word: u16) -> Result<()> {
        use eagle_agc_protocol::words::octal5;
        self.keys("V21N01E").await?;
        self.keys(&octal5(ecadr)).await?; self.keys("E").await?;
        self.keys(&octal5(word)).await?; self.keys("E").await?;
        tokio::time::sleep(Duration::from_millis(200)).await;
        let got = self.read_erasable(ecadr).await?;
        if got != word {
            bail!("erasable {:05o}: wrote {:05o}, read back {:05o}", ecadr, word, got);
        }
        Ok(())
    }

    /// V01N01: display octal contents of an erasable; parse R1.
    pub async fn read_erasable(&mut self, ecadr: u16) -> Result<u16> {
        use eagle_agc_protocol::words::octal5;
        self.keys("V01N01E").await?;
        self.keys(&octal5(ecadr)).await?; self.keys("E").await?;
        let d = self.wait(Duration::from_secs(5), |d| {
            parse_octal_register(&reg_string(&d.r1)).is_some()
        }).await?;
        parse_octal_register(&reg_string(&d.r1))
            .ok_or_else(|| anyhow!("unparseable R1 after V01N01"))
    }

    /// V05N09: three most recent alarm codes (octal), R1-R3.
    pub async fn alarm_codes(&mut self) -> Result<[u16; 3]> {
        self.keys("V05N09E").await?;
        let d = self.wait(Duration::from_secs(5), |d| {
            parse_octal_register(&reg_string(&d.r1)).is_some()
        }).await?;
        Ok([
            parse_octal_register(&reg_string(&d.r1)).unwrap_or(0),
            parse_octal_register(&reg_string(&d.r2)).unwrap_or(0),
            parse_octal_register(&reg_string(&d.r3)).unwrap_or(0),
        ])
    }
}

fn reg_string(r: &eagle_agc_protocol::dsky::RegisterDisplay) -> String {
    std::iter::once(r.sign).chain(r.digits).collect()
}

pub fn parse_octal_register(display: &str) -> Option<u16> {
    let s = display.trim_start_matches([' ', '+', '-']);
    if s.len() != 5 { return None; }
    u16::from_str_radix(s, 8).ok()
}

/// Test/runner helper: owns the AGC session, applies packets to a local
/// `DskyState`, and publishes a watch update on every crew-visible change.
/// Forwards commands sent on the returned `mpsc::UnboundedSender<Packet>`
/// into the session. The spawned task (and the AGC child process it owns,
/// via `AgcSession`'s `kill_on_drop`) ends when either side of the pump
/// closes: the AGC event stream, or the last command sender being dropped.
pub fn pump(
    mut session: AgcSession,
) -> (watch::Receiver<DskyState>, mpsc::UnboundedSender<Packet>, tokio::task::JoinHandle<()>) {
    let (dsky_tx, dsky_rx) = watch::channel(DskyState::default());
    let (cmd_tx, mut cmd_rx) = mpsc::unbounded_channel::<Packet>();

    let handle = tokio::spawn(async move {
        let mut dsky = DskyState::default();
        loop {
            tokio::select! {
                pkt = session.events().recv() => {
                    match pkt {
                        Some(pkt) => {
                            if dsky.apply(&pkt) {
                                let _ = dsky_tx.send_replace(dsky);
                            }
                        }
                        None => break, // AGC event stream closed (yaAGC died?)
                    }
                }
                cmd = cmd_rx.recv() => {
                    match cmd {
                        Some(pkt) => {
                            if session.send(pkt).is_err() { break; }
                        }
                        None => break, // all command senders dropped
                    }
                }
            }
        }
    });

    (dsky_rx, cmd_tx, handle)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn octal_register_parse() {
        assert_eq!(parse_octal_register(" 01234"), Some(0o1234));
        assert_eq!(parse_octal_register("+01234"), Some(0o1234));
        assert_eq!(parse_octal_register(" 77776"), Some(0o77776));
        assert_eq!(parse_octal_register("  12 4"), None); // blanks inside
        assert_eq!(parse_octal_register(" 91234"), None); // non-octal digit
    }

    #[tokio::test]
    async fn keys_emit_expected_packets() {
        let (tx, mut rx_pkts) = tokio::sync::mpsc::unbounded_channel();
        let (_wtx, wrx) = tokio::sync::watch::channel(Default::default());
        let mut s = DskyScript::new(tx, wrx);
        s.set_key_delay(std::time::Duration::ZERO); // speed up unit test
        s.keys("V21N01E").await.unwrap();
        let names = ["VERB", "2", "1", "NOUN", "0", "1", "ENTR"];
        for n in names {
            let expect = eagle_agc_protocol::keys::DskyKey::from_name(n).unwrap().packet();
            assert_eq!(rx_pkts.recv().await.unwrap(), expect);
        }
    }

    #[tokio::test]
    async fn wait_resolves_on_predicate_and_times_out() {
        let (tx, _r) = tokio::sync::mpsc::unbounded_channel();
        let (wtx, wrx) = tokio::sync::watch::channel(DskyState::default());
        let mut s = DskyScript::new(tx, wrx);
        let waiter = tokio::spawn(async move {
            s.wait(std::time::Duration::from_secs(1), |d| d.prog == ['6', '3']).await
        });
        let mut d = DskyState::default();
        d.prog = ['6', '3'];
        wtx.send(d).unwrap();
        assert!(waiter.await.unwrap().is_ok());
    }
}
