"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import NeonShell from "@/components/layout/NeonShell";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SpotInfo {
  texture: string;
  exploitability: number;
  strategy: Record<string, number>;
}

interface PositionCache {
  position: string;
  stack_bb: number;
  spots: Record<string, SpotInfo>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const POSITIONS = ["BTN", "CO", "SB", "HJ", "UTG"];

// Dominant action color
const ACTION_COLORS: Record<string, string> = {
  Check:   "#3f3f46",
  Bet33:   "#0e7490",
  "Bet(0)":"#0e7490",
  Bet75:   "#0284c7",
  "Bet(1)":"#0284c7",
  Bet100:  "#7c3aed",
  "Bet(2)":"#7c3aed",
};

function dominantAction(strategy: Record<string, number>): string {
  return Object.entries(strategy).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "Check";
}

function checkFreqColor(freq: number): string {
  // Low check (aggro) → violet, high check (passive) → zinc
  const r = Math.round(124 * freq + 63 * (1 - freq));
  const g = Math.round(58  * freq + 63 * (1 - freq));
  const b = Math.round(237 * freq + 70 * (1 - freq));
  return `rgb(${r},${g},${b})`;
}

// Texture labels for filter chips
const TEXTURES = [
  "all",
  "monotone", "two_tone", "rainbow",
  "paired", "connected", "semi_connected", "disconnected",
] as const;
type TextureFilter = typeof TEXTURES[number];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ReportPage() {
  const router = useRouter();
  const [pos, setPos] = useState("BTN");
  const [cache, setCache] = useState<PositionCache | null>(null);
  const [loading, setLoading] = useState(false);
  const [colorMode, setColorMode] = useState<"dominant" | "check">("check");
  const [textureFilter, setTextureFilter] = useState<TextureFilter>("all");

  useEffect(() => {
    setCache(null);
    setLoading(true);
    fetch(`/solutions/cache/${pos}_100.json`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { setCache(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [pos]);

  const spots = useMemo(() => {
    if (!cache) return [];
    return Object.entries(cache.spots)
      .filter(([, info]) =>
        textureFilter === "all" || info.texture.includes(textureFilter)
      )
      .sort(([a], [b]) => a.localeCompare(b));
  }, [cache, textureFilter]);

  function cellColor(info: SpotInfo): string {
    if (colorMode === "dominant") {
      const act = dominantAction(info.strategy);
      return ACTION_COLORS[act] ?? "#3f3f46";
    }
    return checkFreqColor(info.strategy["Check"] ?? 0);
  }

  const rightSlot = (
    <>
      <div className="flex gap-1">
        {POSITIONS.map(p => (
          <button key={p} onClick={() => setPos(p)}
            className={`px-2 py-0.5 text-xs tracking-widest border transition-all
              ${pos === p ? "border-cyan-400 text-cyan-300 bg-cyan-400/10" : "border-zinc-700 text-zinc-500 hover:border-zinc-500"}`}>
            {p}
          </button>
        ))}
      </div>
      <span className="text-zinc-600">vs BB · 100bb</span>
      <span
        className="ml-2 px-1.5 py-0.5 border border-amber-500/40 text-amber-400 text-[9px] tracking-widest"
        title="gto-cuda single-street solves over uniform ranges. For exact equilibria use the SOLVER page (gto-hu)."
      >
        PREVIEW — approximation
      </span>
    </>
  );

  return (
    <NeonShell rightSlot={rightSlot}>
      <div className="flex flex-col h-full">

        {/* Controls */}
        <div className="flex items-center gap-4 px-5 py-2 border-b border-cyan-500/10 flex-wrap">
          {/* Color mode */}
          <div className="flex gap-1 items-center">
            <span className="text-[9px] text-zinc-600 tracking-widest mr-1">COLOR</span>
            {(["check", "dominant"] as const).map(m => (
              <button key={m} onClick={() => setColorMode(m)}
                className={`px-2 py-0.5 text-[10px] border transition-all
                  ${colorMode === m ? "border-cyan-400/60 text-cyan-300" : "border-zinc-700 text-zinc-600 hover:border-zinc-500"}`}>
                {m === "check" ? "CHECK %" : "DOMINANT"}
              </button>
            ))}
          </div>

          {/* Texture filter */}
          <div className="flex gap-1 flex-wrap items-center">
            <span className="text-[9px] text-zinc-600 tracking-widest mr-1">TEXTURE</span>
            {TEXTURES.map(t => (
              <button key={t} onClick={() => setTextureFilter(t)}
                className={`px-2 py-0.5 text-[10px] border transition-all
                  ${textureFilter === t ? "border-cyan-400/60 text-cyan-300" : "border-zinc-700 text-zinc-600 hover:border-zinc-500"}`}>
                {t.toUpperCase()}
              </button>
            ))}
          </div>

          <span className="ml-auto text-[10px] text-zinc-600">
            {spots.length} / {Object.keys(cache?.spots ?? {}).length} flops
          </span>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 px-5 py-1.5 border-b border-cyan-500/10">
          {colorMode === "check" ? (
            <>
              <span className="text-[9px] text-zinc-600 tracking-widest">CHECK %</span>
              <div className="flex items-center gap-1">
                <span className="text-[9px] text-violet-400">BET (0%)</span>
                <div className="w-20 h-2 rounded" style={{
                  background: "linear-gradient(to right, #7c3aed, #3f3f46)"
                }} />
                <span className="text-[9px] text-zinc-400">CHECK (100%)</span>
              </div>
            </>
          ) : (
            <>
              <span className="text-[9px] text-zinc-600 tracking-widest">DOMINANT ACTION</span>
              {Object.entries(ACTION_COLORS).filter(([k]) => !k.includes("(")).map(([action, color]) => (
                <div key={action} className="flex items-center gap-1">
                  <div className="w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
                  <span className="text-[9px] text-zinc-500">{action}</span>
                </div>
              ))}
            </>
          )}
        </div>

        {/* Grid */}
        <div className="flex-1 overflow-auto p-4">
          {loading && (
            <div className="flex items-center justify-center h-full text-zinc-600 text-xs animate-pulse tracking-widest">
              LOADING CACHE…
            </div>
          )}

          {!loading && !cache && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-2">
                <p className="text-zinc-500 text-xs tracking-widest">NO CACHE AVAILABLE FOR {pos}</p>
                <p className="text-zinc-700 text-[10px]">Run batch computation first.</p>
              </div>
            </div>
          )}

          {!loading && cache && spots.length === 0 && (
            <div className="flex items-center justify-center h-full text-zinc-600 text-xs">
              No flops match the selected texture filter.
            </div>
          )}

          {!loading && spots.length > 0 && (
            <div
              className="grid gap-0.5"
              style={{ gridTemplateColumns: "repeat(auto-fill, minmax(48px, 1fr))" }}
            >
              {spots.map(([board, info]) => {
                const ranks = [board.slice(0, 1), board.slice(2, 3), board.slice(4, 5)];
                const checkPct = Math.round((info.strategy["Check"] ?? 0) * 100);
                return (
                  <button
                    key={board}
                    onClick={() => router.push(`/library?board=${board}&position=${pos}`)}
                    title={`${board}\nCheck ${checkPct}%\n${info.texture}`}
                    className="group relative aspect-square rounded-sm flex flex-col items-center justify-center gap-0 transition-all hover:scale-105 hover:z-10 hover:ring-1 hover:ring-cyan-400"
                    style={{ background: cellColor(info) }}
                  >
                    <span className="text-[9px] font-bold text-white/90 leading-none tracking-tight">
                      {ranks.join("")}
                    </span>
                    <span className="text-[7px] text-white/50 leading-none mt-0.5">
                      {checkPct}%
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </NeonShell>
  );
}
