/** /terms — 利用規約 (弁護士レビュー前草案) */
export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)] px-4 py-12">
      <div className="max-w-3xl mx-auto">
        <div className="text-[10px] font-mono text-[var(--warn)] border border-[var(--warn)] px-3 py-2 mb-8">
          ⚠ この利用規約は草案です。弁護士レビュー未了。β公開前に専門家確認予定。
        </div>

        <h1 className="text-2xl font-bold mb-2">利用規約</h1>
        <p className="text-[11px] text-[var(--text-muted)] mb-8">最終更新: 草案 (未施行)</p>

        {[
          {
            title: "第1条 (本サービスの目的)",
            body: "re_invest_os（以下「本サービス」）は、個人投資家が不動産投資物件を検討する際の参考情報を提供することを目的とした分析支援ツールです。本サービスは投資助言業務を行うものではなく、投資判断の最終責任はユーザー本人にあります。",
          },
          {
            title: "第2条 (免責事項)",
            body: "本サービスの分析結果はパラメトリック・シミュレーションであり、将来の収益・損失を保証するものではありません。表示される数値は入力した前提条件に基づく計算値であり、市場環境・金利・空室率・修繕費等の変動により実際の結果は大きく異なることがあります。本サービスの使用によって生じた損害について、サービス提供者は一切の責任を負いません。",
          },
          {
            title: "第3条 (禁止事項)",
            body: "ユーザーは以下の行為を行ってはなりません。\n(1) 本サービスの分析結果を第三者への投資勧誘に使用すること\n(2) 本サービスのシステムに不正アクセスを行うこと\n(3) 本サービスを通じて虚偽の情報を送信すること\n(4) 法令または公序良俗に反する行為",
          },
          {
            title: "第4条 (個人情報の取扱い)",
            body: "個人情報の取扱いについては、別途プライバシーポリシーに定めます。本サービスはユーザーの問い合わせ情報を不動産業者・第三者に提供・販売しません。",
          },
          {
            title: "第5条 (規約の変更)",
            body: "サービス提供者は、必要と判断した場合に本規約を変更することができます。変更後の規約はサービス上に掲示した時点から効力を生じます。",
          },
          {
            title: "第6条 (準拠法・裁判管轄)",
            body: "本規約は日本法を準拠法とし、本サービスに関する紛争については、サービス提供者の所在地を管轄する裁判所を第一審の専属的合意管轄裁判所とします。",
          },
        ].map(({ title, body }) => (
          <section key={title} className="mb-8">
            <h2 className="font-bold text-sm mb-2">{title}</h2>
            <p className="text-[12px] text-[var(--text-muted)] leading-relaxed whitespace-pre-line">
              {body}
            </p>
          </section>
        ))}

        <p className="text-[11px] text-[var(--text-subtle)] mt-12 border-t border-[var(--border)] pt-4">
          <a href="/lp" className="text-[var(--accent)] hover:underline">← トップに戻る</a>
          &nbsp;|&nbsp;
          <a href="/privacy" className="text-[var(--accent)] hover:underline">プライバシーポリシー</a>
          &nbsp;|&nbsp;
          <a href="/tokutei" className="text-[var(--accent)] hover:underline">特定商取引法</a>
        </p>
      </div>
    </div>
  );
}
