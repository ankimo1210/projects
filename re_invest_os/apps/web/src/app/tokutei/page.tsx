/** /tokutei — 特定商取引法に基づく表記 (弁護士レビュー前草案) */
export default function TokuteiPage() {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)] px-4 py-12">
      <div className="max-w-3xl mx-auto">
        <div className="text-[10px] font-mono text-[var(--warn)] border border-[var(--warn)] px-3 py-2 mb-8">
          ⚠ 草案。弁護士・税理士確認前。β公開前に実際の事業者情報を記入してください。
        </div>

        <h1 className="text-2xl font-bold mb-8">特定商取引法に基づく表記</h1>

        <table className="w-full border border-[var(--border)] text-[12px]">
          <tbody>
            {[
              ["販売業者", "【β公開前に記入】"],
              ["代表者名", "【記入】"],
              ["所在地", "請求があれば遅滞なく開示します"],
              ["電話番号", "請求があれば遅滞なく開示します"],
              ["メールアドレス", "【記入 — 公開用メール】"],
              ["サービス名称", "re_invest_os"],
              ["サービス内容", "不動産投資物件の財務分析・買付前監査支援ツール"],
              ["料金", "無料プラン: 月〇回まで無料 / Proプラン: 月〇〇〇円 (税込) — β期間中は無料"],
              ["支払方法", "クレジットカード (Visa・Mastercard・JCB)"],
              ["支払時期", "月額課金: 各月の決済日に翌月分を前払い"],
              ["サービス提供時期", "決済完了後即時"],
              ["返品・キャンセル", "デジタルサービスの性質上、提供開始後の返金は原則不可。ただし重大な障害がある場合はご相談ください。"],
              ["動作環境", "最新版の Chrome / Firefox / Safari / Edge を推奨。Internet Explorer 非対応。"],
            ].map(([key, value]) => (
              <tr key={key} className="border-t border-[var(--border)]">
                <td className="px-3 py-2 bg-[var(--surface)] text-[var(--text-muted)] font-bold w-40 align-top">
                  {key}
                </td>
                <td className="px-3 py-2 leading-relaxed text-[var(--text)]">{value}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <p className="text-[11px] text-[var(--text-subtle)] mt-12 border-t border-[var(--border)] pt-4">
          <a href="/lp" className="text-[var(--accent)] hover:underline">← トップに戻る</a>
          &nbsp;|&nbsp;
          <a href="/terms" className="text-[var(--accent)] hover:underline">利用規約</a>
          &nbsp;|&nbsp;
          <a href="/privacy" className="text-[var(--accent)] hover:underline">プライバシーポリシー</a>
        </p>
      </div>
    </div>
  );
}
