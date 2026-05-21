/** /privacy — プライバシーポリシー (弁護士レビュー前草案) */
export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)] px-4 py-12">
      <div className="max-w-3xl mx-auto">
        <div className="text-[10px] font-mono text-[var(--warn)] border border-[var(--warn)] px-3 py-2 mb-8">
          ⚠ 草案。弁護士レビュー未了。β公開前に専門家確認予定。
        </div>

        <h1 className="text-2xl font-bold mb-2">プライバシーポリシー</h1>
        <p className="text-[11px] text-[var(--text-muted)] mb-8">最終更新: 草案 (未施行)</p>

        {[
          {
            title: "1. 取得する情報",
            body: "本サービスは以下の情報を取得する場合があります。\n・ご利用の物件資料 (URL・PDF)\n・分析実行時の入力パラメータ\n・アカウント登録時のメールアドレス (β以降)\n・サービス改善のためのアクセスログ",
          },
          {
            title: "2. PII (個人情報) の取扱い",
            body: "アップロードされた資料から個人名・電話番号・メールアドレス等の個人情報 (PII) が検出された場合、LLM への送信前に自動的にマスク処理を行います。マスクされたデータのみがAI分析に使用されます。",
          },
          {
            title: "3. 業者への情報提供",
            body: "本サービスはユーザーの問い合わせ情報・連絡先・閲覧した物件情報を不動産業者・仲介会社・第三者に提供・販売しません。これは本サービスの根本的な差別化方針です。",
          },
          {
            title: "4. アップロードファイルの保存期間",
            body: "アップロードされたPDF等のファイルは、最大30日間保存後に自動削除されます。分析結果のメタデータは引き続き保存される場合があります。",
          },
          {
            title: "5. Cookie・解析ツール",
            body: "本サービスはサービス改善のために匿名のアクセス解析ツール (PostHog等) を使用する場合があります。個人を特定できない形での利用統計のみを収集します。",
          },
          {
            title: "6. 情報の開示",
            body: "法令に基づく開示要請がある場合を除き、取得した情報を第三者に開示することはありません。",
          },
          {
            title: "7. お問い合わせ",
            body: "個人情報の取扱いに関するお問い合わせは、サービス内のお問い合わせフォームまたは公開メールアドレスにご連絡ください。",
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
          <a href="/terms" className="text-[var(--accent)] hover:underline">利用規約</a>
          &nbsp;|&nbsp;
          <a href="/tokutei" className="text-[var(--accent)] hover:underline">特定商取引法</a>
        </p>
      </div>
    </div>
  );
}
