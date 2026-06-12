"use client";

import { useRef, useState } from "react";
import {
  cancelJob,
  customSolve,
  solveFlopAsync,
  JobStatus,
  SolveRequest,
  SolveResult,
} from "@/lib/solve-api";

const DEFAULT_BOARD = "Ah Kd 7s 2c 9h";

// Shared neon input/select styling (matches solver/page.tsx + hu/page.tsx idiom).
const FIELD =
  "mt-1 w-full bg-zinc-900 border border-zinc-700 rounded-sm px-2 py-1.5 text-xs " +
  "text-zinc-200 font-mono focus:border-cyan-500/60 focus:outline-none transition-colors";
const FIELD_LABEL = "text-[9px] tracking-widest text-cyan-500/60";

export default function CustomSolve() {
  const [board, setBoard] = useState(DEFAULT_BOARD);
  const [potBb, setPotBb] = useState(20);
  const [stackBb, setStackBb] = useState(90);
  const [potType, setPotType] = useState<"srp" | "3bet" | "4bet">("srp");
  const [rake, setRake] = useState<"none" | "site" | "live">("none");
  const [oopRange, setOopRange] = useState("");
  const [ipRange, setIpRange] = useState("");
  const [betSizes, setBetSizes] = useState("");
  const [iterations, setIterations] = useState(0); // 0 = server default
  const [bucketsRiver, setBucketsRiver] = useState(128);
  const [bucketsTurn, setBucketsTurn] = useState(0);
  const [maxTableGb, setMaxTableGb] = useState(12);
  const [result, setResult] = useState<SolveResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [job, setJob] = useState<JobStatus | null>(null);
  const jobIdRef = useRef<string | null>(null);

  const cards = board.trim().split(/\s+/).filter(Boolean);
  const street =
    cards.length === 5 ? "river" : cards.length === 4 ? "turn+river" : cards.length === 3 ? "flop" : "unsupported";
  const isFlop = street === "flop";

  function buildReq(): SolveRequest {
    return {
      stack_bb: stackBb,
      // flop has no rake path; force none.
      rake: { model: isFlop ? "none" : rake },
      ...(iterations > 0 ? { iterations } : {}),
      config: {
        pot_bb: potBb,
        // flop only supports srp / 3bet
        pot_type: isFlop && potType === "4bet" ? "srp" : potType,
        board: cards,
        ranges: {
          ...(ipRange.trim() ? { ip: ipRange.trim() } : {}),
          ...(oopRange.trim() ? { oop: oopRange.trim() } : {}),
        },
        ...(betSizes.trim()
          ? {
              action_tree: {
                bet_sizes_pct: betSizes.split(",").map((s) => parseInt(s.trim(), 10)),
              },
            }
          : {}),
        ...(isFlop
          ? {
              abstraction: {
                buckets_river: bucketsRiver,
                buckets_turn: bucketsTurn,
                max_table_gb: maxTableGb,
              },
            }
          : {}),
      },
    };
  }

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    setJob(null);
    try {
      if (isFlop) {
        const res = await solveFlopAsync(
          buildReq(),
          (s) => setJob(s),
          (h) => {
            jobIdRef.current = h.job_id;
          },
        );
        setResult(res);
      } else {
        setResult(await customSolve(buildReq()));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
      jobIdRef.current = null;
    }
  }

  async function cancel() {
    if (jobIdRef.current) await cancelJob(jobIdRef.current);
  }

  const canSolve = !busy && street !== "unsupported";
  const abstraction = result?.meta.abstraction;

  return (
    <section className="mt-2 border border-cyan-500/20 rounded-sm p-5 bg-cyan-400/[0.02]">
      <p className="text-[9px] tracking-widest text-cyan-500/40">
        CUSTOM SOLVE
        <span className="ml-2 text-zinc-600 normal-case tracking-normal">
          gto-hu equilibrium — exact exploitability
        </span>
      </p>

      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <label className={FIELD_LABEL}>
          BOARD (3=FLOP, 4=TURN, 5=RIVER)
          <input className={FIELD} value={board} onChange={(e) => setBoard(e.target.value)} />
        </label>
        <label className={FIELD_LABEL}>
          POT (BB)
          <input type="number" className={FIELD} value={potBb} onChange={(e) => setPotBb(+e.target.value)} />
        </label>
        <label className={FIELD_LABEL}>
          EFF. STACK (BB)
          <input type="number" className={FIELD} value={stackBb} onChange={(e) => setStackBb(+e.target.value)} />
        </label>
        <label className={FIELD_LABEL}>
          POT TYPE
          <select
            className={FIELD}
            value={potType}
            onChange={(e) => setPotType(e.target.value as typeof potType)}
          >
            <option value="srp">SRP</option>
            <option value="3bet">3bet pot</option>
            <option value="4bet" disabled={isFlop}>
              4bet pot{isFlop ? " (n/a flop)" : ""}
            </option>
          </select>
        </label>
        <label className={FIELD_LABEL}>
          RAKE
          <select
            className={FIELD}
            value={isFlop ? "none" : rake}
            disabled={isFlop}
            onChange={(e) => setRake(e.target.value as typeof rake)}
          >
            <option value="none">None{isFlop ? " (flop only)" : ""}</option>
            <option value="site">Site (5% / 3bb)</option>
            <option value="live">Live (10% / 5bb)</option>
          </select>
        </label>
        <label className={FIELD_LABEL}>
          OOP RANGE (BLANK = UNIFORM)
          <input
            className={FIELD}
            placeholder="QQ,JJ,AKs:0.5"
            value={oopRange}
            onChange={(e) => setOopRange(e.target.value)}
          />
        </label>
        <label className={FIELD_LABEL}>
          IP RANGE (BLANK = UNIFORM)
          <input className={FIELD} placeholder="AA,KK,AQo" value={ipRange} onChange={(e) => setIpRange(e.target.value)} />
        </label>
        <label className={FIELD_LABEL}>
          BET SIZES %POT (BLANK = DEFAULT)
          <input className={FIELD} placeholder="50,100" value={betSizes} onChange={(e) => setBetSizes(e.target.value)} />
        </label>
        <label className={FIELD_LABEL}>
          ITERATIONS (0 = DEFAULT)
          <input type="number" className={FIELD} value={iterations} onChange={(e) => setIterations(+e.target.value)} />
        </label>
      </div>

      {/* Flop-only abstraction controls (bucketing is mandatory on flop). */}
      {isFlop && (
        <div className="mt-3 grid grid-cols-3 gap-3 md:grid-cols-6">
          <label className={FIELD_LABEL}>
            RIVER BUCKETS
            <input
              type="number"
              className={FIELD}
              value={bucketsRiver}
              onChange={(e) => setBucketsRiver(+e.target.value)}
            />
          </label>
          <label className={FIELD_LABEL}>
            TURN BUCKETS (0=EXACT)
            <input
              type="number"
              className={FIELD}
              value={bucketsTurn}
              onChange={(e) => setBucketsTurn(+e.target.value)}
            />
          </label>
          <label className={FIELD_LABEL}>
            MAX TABLE (GB)
            <input
              type="number"
              className={FIELD}
              value={maxTableGb}
              onChange={(e) => setMaxTableGb(+e.target.value)}
            />
          </label>
        </div>
      )}

      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={run}
          disabled={!canSolve}
          className={`px-8 py-2 text-xs tracking-[0.3em] border rounded-sm transition-all
            ${
              canSolve
                ? "border-cyan-400 text-cyan-300 hover:bg-cyan-400/10"
                : "border-zinc-700 text-zinc-600 cursor-not-allowed"
            }`}
          style={canSolve ? { boxShadow: "0 0 12px rgba(34,211,238,0.3)" } : undefined}
        >
          {busy ? "SOLVING…" : `SOLVE ${street.toUpperCase()} →`}
        </button>
        {busy && isFlop && (
          <button
            onClick={cancel}
            className="px-4 py-2 text-[10px] tracking-widest border border-rose-500/40 text-rose-400 rounded-sm hover:bg-rose-500/10"
          >
            CANCEL
          </button>
        )}
      </div>

      {street === "turn+river" && (
        <p className="mt-2 text-[10px] text-amber-400/80 tracking-wide">
          turn+river runs ~10–40 s synchronously — keep the tab open.
        </p>
      )}
      {isFlop && (
        <p className="mt-2 text-[10px] text-amber-400/80 tracking-wide">
          flop is an async job — it runs in the background and can take many minutes at quality settings.
          Exploitability already includes the bucketing abstraction loss.
        </p>
      )}

      {/* Live job status while a flop solve is queued/running. */}
      {busy && job && (
        <div className="mt-3 border border-cyan-500/20 rounded-sm p-3 text-[11px] text-cyan-300/80 font-mono">
          job {job.status.toUpperCase()}
          {job.status === "queued" && ` · waiting for a memory slot (${job.est_gb.toFixed(1)} GB)`}
          {job.elapsed_s != null && ` · ${job.elapsed_s.toFixed(0)}s elapsed`}
        </div>
      )}

      {error && (
        <div className="mt-3 bg-rose-900/20 border border-rose-500/30 rounded-sm p-3 text-[11px] text-rose-400 max-w-xl">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 space-y-4 max-w-2xl">
          <div
            className="border border-cyan-400/40 bg-cyan-400/5 rounded-sm p-3 text-[11px] text-cyan-200 font-mono leading-relaxed"
            style={{ boxShadow: "0 0 16px rgba(34,211,238,0.12)" }}
          >
            exploitability {result.exploitability.per_hand_bb.toFixed(4)} bb/hand (NashConv{" "}
            {result.exploitability.nashconv_bb.toFixed(4)})
            {result.equity && ` · equity IP ${(result.equity.ip * 100).toFixed(1)}%`} · EV IP{" "}
            {result.ev.ip.toFixed(3)} / OOP {result.ev.oop.toFixed(3)} bb · {result.meta.elapsed_s.toFixed(1)}s /{" "}
            {result.meta.iterations} iters
          </div>

          {abstraction && (
            <div className="inline-flex items-center gap-2 border border-amber-500/40 bg-amber-500/10 rounded-sm px-3 py-1 text-[10px] text-amber-300 tracking-wide">
              ABSTRACTION · river buckets {abstraction.buckets_river} · turn buckets{" "}
              {abstraction.buckets_turn === 0 ? "exact" : abstraction.buckets_turn}
              {result.meta.table_gb != null && ` · ${result.meta.table_gb.toFixed(1)} GB`}
            </div>
          )}

          <div>
            <p className="text-[9px] tracking-widest text-cyan-500/40 mb-2">OOP ROOT STRATEGY</p>
            <table className="w-full text-left text-[11px] text-zinc-300">
              <thead>
                <tr className="text-cyan-500/50 text-[9px] tracking-widest">
                  <th className="py-1 font-normal">ACTION</th>
                  <th className="py-1 font-normal">FREQ</th>
                </tr>
              </thead>
              <tbody>
                {result.strategy.map((s) => (
                  <tr key={s.action} className="border-t border-zinc-800">
                    <td className="py-1 font-mono">{s.action}</td>
                    <td className="py-1 font-mono text-zinc-200">{(s.freq * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
