/**
 * LP (ランディングページ)
 *
 * ターゲット: 区分マンション / 一棟物件を検討中の個人投資家
 * トーン: 業者送客しない / 数字で話す / 冷静
 * デザイン: クリーン基調 (Bloomberg ではない)
 */
import Link from "next/link";

function StatBox({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center px-6 py-4 border border-[var(--border)] bg-[var(--surface)]">
      <div className="text-3xl font-mono font-bold text-[var(--accent)] tabular-nums">{value}</div>
      <div className="text-[11px] text-[var(--text-muted)] mt-1 font-mono uppercase tracking-widest">
        {label}
      </div>
    </div>
  );
}

function FeatureRow({
  icon,
  title,
  desc,
}: {
  icon: string;
  title: string;
  desc: string;
}) {
  return (
    <div className="flex gap-4 items-start">
      <span className="text-2xl mt-0.5">{icon}</span>
      <div>
        <h3 className="font-bold text-sm mb-0.5">{title}</h3>
        <p className="text-[12px] text-[var(--text-muted)] leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

function CompareRow({
  label,
  them,
  us,
}: {
  label: string;
  them: string;
  us: string;
}) {
  return (
    <tr className="border-t border-[var(--border)] text-[12px]">
      <td className="px-3 py-2 text-[var(--text-muted)]">{label}</td>
      <td className="px-3 py-2 text-[var(--text-muted)] text-center line-through opacity-50">
        {them}
      </td>
      <td className="px-3 py-2 text-[var(--good)] text-center font-bold">{us}</td>
    </tr>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
        <div className="font-mono font-bold text-[var(--accent)] tracking-widest">
          RE_INVEST_OS
        </div>
        <nav className="flex items-center gap-4 text-[12px]">
          <Link href="/new" className="text-[var(--text-muted)] hover:text-[var(--text)]">
            手動入力
          </Link>
          <Link href="/" className="text-[var(--text-muted)] hover:text-[var(--text)]">
            デモ
          </Link>
          <Link
            href="/upload"
            className="px-4 py-1.5 bg-[var(--accent)] text-[var(--bg)] font-mono font-bold text-[11px] uppercase tracking-widest hover:opacity-90"
          >
            無料で試す
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-block px-3 py-1 border border-[var(--accent)] text-[var(--accent)] font-mono text-[10px] uppercase tracking-widest mb-6">
          業者送客なし / 営業メール不要
        </div>
        <h1 className="text-4xl md:text-5xl font-bold leading-tight mb-6">
          物件資料を貼るだけで
          <br />
          <span style={{ color: "var(--accent)" }}>30秒</span>で買付前監査
        </h1>
        <p className="text-[var(--text-muted)] text-base max-w-2xl mx-auto mb-10 leading-relaxed">
          表面利回り 6.2% に見えても、融資・税・修繕を考えると実質赤字というケースは珍しくありません。
          <br />
          re_invest_os は資料 URL または PDF を投入するだけで、キャッシュフロー・DSCR・出口まで数秒で計算します。
        </p>
        <Link
          href="/upload"
          className="inline-block px-8 py-4 bg-[var(--accent)] text-[var(--bg)] font-mono font-bold text-sm uppercase tracking-widest hover:opacity-90"
        >
          無料で監査を始める →
        </Link>
        <p className="text-[11px] text-[var(--text-subtle)] mt-4">
          登録不要 · クレジットカード不要 · 物件情報は業者に送りません
        </p>
      </section>

      {/* Demo result teaser */}
      <section className="max-w-4xl mx-auto px-6 pb-16">
        <div className="border border-[var(--border)] bg-[var(--surface)] p-6">
          <div className="text-[10px] font-mono uppercase tracking-widest text-[var(--accent)] mb-4">
            DEMO — 西新宿レジデンス 504号 (価格 3,980万円 / 表面利回り 6.2%)
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div className="text-center">
              <div className="text-[10px] text-[var(--text-muted)] font-mono uppercase mb-1">
                NOI Cap
              </div>
              <div className="text-xl font-mono font-bold" style={{ color: "var(--warn)" }}>
                2.99%
              </div>
              <div className="text-[9px] text-[var(--text-subtle)]">表面 6.2% より大きく低下</div>
            </div>
            <div className="text-center">
              <div className="text-[10px] text-[var(--text-muted)] font-mono uppercase mb-1">
                DSCR Y1
              </div>
              <div className="text-xl font-mono font-bold" style={{ color: "var(--bad)" }}>
                0.96
              </div>
              <div className="text-[9px] text-[var(--text-subtle)]">1.0 を下回り CF 赤字</div>
            </div>
            <div className="text-center">
              <div className="text-[10px] text-[var(--text-muted)] font-mono uppercase mb-1">
                ATCF Y1
              </div>
              <div className="text-xl font-mono font-bold" style={{ color: "var(--bad)" }}>
                -¥45K
              </div>
              <div className="text-[9px] text-[var(--text-subtle)]">初年度から毎月持ち出し</div>
            </div>
            <div className="text-center">
              <div className="text-[10px] text-[var(--text-muted)] font-mono uppercase mb-1">
                Score
              </div>
              <div className="text-xl font-mono font-bold" style={{ color: "var(--bad)" }}>
                36.5
              </div>
              <div className="text-[9px] text-[var(--text-subtle)]">要警戒</div>
            </div>
          </div>
          <Link
            href="/"
            className="text-[11px] text-[var(--accent)] hover:underline font-mono"
          >
            → このデモの詳細レポートを見る
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="max-w-4xl mx-auto px-6 pb-16">
        <div className="grid grid-cols-3 gap-3">
          <StatBox value="9" label="API エンドポイント" />
          <StatBox value="127" label="自動テスト" />
          <StatBox value="100%" label="楽待 fixture 精度" />
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-4xl mx-auto px-6 pb-16">
        <h2 className="text-xl font-bold mb-8 text-center">使い方 3ステップ</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              step: "01",
              title: "URL or PDF を投入",
              desc: "楽待・SUUMO の物件ページ URL、または販売図面 PDF をドロップするだけ。",
            },
            {
              step: "02",
              title: "AI 抽出を確認",
              desc: "AI が読み取った価格・賃料・構造等を確認画面で修正。前提条件を自分でコントロール。",
            },
            {
              step: "03",
              title: "監査レポートを読む",
              desc: "NOI Cap・DSCR・IRR・出口損益・AI 所見・仲介への確認質問が揃う。判断は自分で。",
            },
          ].map((s) => (
            <div key={s.step} className="border border-[var(--border)] p-5">
              <div className="font-mono text-[var(--accent)] font-bold text-lg mb-2">{s.step}</div>
              <h3 className="font-bold mb-2">{s.title}</h3>
              <p className="text-[12px] text-[var(--text-muted)] leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-4xl mx-auto px-6 pb-16">
        <h2 className="text-xl font-bold mb-8 text-center">なぜ re_invest_os か</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <FeatureRow
            icon="🔒"
            title="業者送客しない"
            desc="あなたの問い合わせ情報を不動産業者に売ることはありません。資料閲覧が営業電話につながらない。"
          />
          <FeatureRow
            icon="🧮"
            title="計算は純粋関数"
            desc="LLM に数字を計算させません。cashflow・DSCR・IRR・減価償却はすべて数値エンジンで。バグがあればテストが壊れる。"
          />
          <FeatureRow
            icon="📋"
            title="前提を透明に"
            desc="空室率・金利・出口 Cap などの前提条件を確認画面で自分で変更できます。ブラックボックスではない。"
          />
          <FeatureRow
            icon="🤝"
            title="買わない選択肢も提示"
            desc="スコアが低い物件には「要警戒」と表示します。賞賛一色の商品紹介サイトとは目的が違います。"
          />
        </div>
      </section>

      {/* Compare table */}
      <section className="max-w-4xl mx-auto px-6 pb-16">
        <h2 className="text-xl font-bold mb-6 text-center">一般的な不動産サイトとの違い</h2>
        <div className="border border-[var(--border)] overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-[var(--surface-alt)]">
                <th className="px-3 py-2 text-left text-[10px] font-mono uppercase tracking-widest text-[var(--text-muted)]">
                  項目
                </th>
                <th className="px-3 py-2 text-center text-[10px] font-mono uppercase tracking-widest text-[var(--text-muted)]">
                  一般サイト
                </th>
                <th className="px-3 py-2 text-center text-[10px] font-mono uppercase tracking-widest text-[var(--accent)]">
                  re_invest_os
                </th>
              </tr>
            </thead>
            <tbody>
              <CompareRow label="目的" them="業者への送客" us="投資家の判断支援" />
              <CompareRow label="収益モデル" them="リード課金・広告" us="直接課金のみ" />
              <CompareRow label="スコア計算" them="なし / 不透明" us="純粋関数 + テスト" />
              <CompareRow label="個人情報" them="業者に共有" us="PIIマスク / 非共有" />
              <CompareRow label="前提変更" them="不可" us="確認画面で可" />
            </tbody>
          </table>
        </div>
      </section>

      {/* Disclaimer */}
      <section className="max-w-4xl mx-auto px-6 pb-8">
        <p className="text-[10px] text-[var(--text-subtle)] font-mono leading-relaxed border border-[var(--border)] bg-[var(--surface)] px-3 py-2">
          [ 免責 ] 本ツールの分析結果は参考情報であり、投資を推奨するものではありません。
          表示される数値はパラメトリック・シミュレーションであり、将来の収益を保証しません。
          投資判断の最終責任はご自身にあります。税務・法務については専門家にご相談ください。
        </p>
      </section>

      {/* CTA bottom */}
      <section className="py-16 text-center border-t border-[var(--border)]">
        <h2 className="text-2xl font-bold mb-4">まず1件、試してみませんか</h2>
        <p className="text-[var(--text-muted)] text-sm mb-8">
          登録不要。楽待・SUUMO の URL を貼るか、販売図面 PDF をドロップするだけです。
        </p>
        <Link
          href="/upload"
          className="inline-block px-8 py-4 bg-[var(--accent)] text-[var(--bg)] font-mono font-bold text-sm uppercase tracking-widest hover:opacity-90"
        >
          無料で監査を始める →
        </Link>
      </section>

      <footer className="text-center py-6 text-[10px] text-[var(--text-subtle)] font-mono border-t border-[var(--border)]">
        <div className="mb-2">© re_invest_os v0.1 · ソロ開発 · 業者送客なし</div>
        <div className="flex items-center justify-center gap-4">
          <Link href="/terms" className="hover:text-[var(--text)]">利用規約</Link>
          <span>·</span>
          <Link href="/privacy" className="hover:text-[var(--text)]">プライバシーポリシー</Link>
          <span>·</span>
          <Link href="/tokutei" className="hover:text-[var(--text)]">特定商取引法</Link>
          <span>·</span>
          <Link href="/history" className="hover:text-[var(--text)]">履歴</Link>
        </div>
      </footer>
    </div>
  );
}
