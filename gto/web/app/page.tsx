import Link from "next/link";

const PAGES = [
  {
    href: "/neon",
    label: "Trainer",
    desc: "プリフロップ GTO トレーナー。クイズ形式でアクション頻度と EV 損失を学ぶ。",
    badge: "Main",
  },
  {
    href: "/library",
    label: "Solution Library",
    desc: "事前計算済み GTO 解をレンジグリッドで閲覧。コンボ別戦略をヒートマップ表示。",
    badge: "Library",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-[#070710] text-white flex items-center justify-center font-mono">
      <div className="max-w-lg w-full px-8">
        <h1 className="text-2xl font-bold tracking-[0.3em] text-cyan-400 mb-1"
          style={{ textShadow: "0 0 20px rgba(34,211,238,0.6)" }}>
          GTO://SUITE
        </h1>
        <p className="text-zinc-600 text-xs tracking-widest mb-10">POKER ANALYSIS PLATFORM</p>

        <div className="flex flex-col gap-3">
          {PAGES.map((p) => (
            <Link
              key={p.href}
              href={p.href}
              className="block border border-cyan-500/20 rounded-xl p-5 hover:border-cyan-400/60 hover:bg-cyan-400/5 transition-all group"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold tracking-widest text-cyan-300 group-hover:text-cyan-200">
                  {p.label}
                </span>
                <span className="text-[10px] border border-cyan-500/30 text-cyan-600 px-2 py-0.5 rounded tracking-widest">
                  {p.badge}
                </span>
              </div>
              <p className="text-xs text-zinc-500">{p.desc}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
