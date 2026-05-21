/**
 * /upload — 物件 URL または PDF を投入する入口画面
 *
 * デザイン: Bloomberg ではなく、クリーン・親しみやすい (LP 想定の延長)
 * フロー:
 *   ユーザー入力 → /api/extract/url or /api/extract/document
 *   → sessionStorage に保存 → /confirm へ遷移
 */
"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

type ExtractionMode = "url" | "pdf";

export default function UploadPage() {
  const router = useRouter();
  const [mode, setMode] = useState<ExtractionMode>("url");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function submit() {
    setError(null);
    setLoading(true);
    setProgress("AI で資料を読み取っています (10〜30秒)…");
    try {
      let resp: Response;
      if (mode === "url") {
        if (!url.trim()) {
          setError("URL を入力してください");
          setLoading(false);
          setProgress(null);
          return;
        }
        resp = await fetch("/api/extract/url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: url.trim() }),
        });
      } else {
        if (!file) {
          setError("PDF を選択してください");
          setLoading(false);
          setProgress(null);
          return;
        }
        const form = new FormData();
        form.append("file", file);
        resp = await fetch("/api/extract/document", { method: "POST", body: form });
      }
      const text = await resp.text();
      if (!resp.ok) {
        try {
          const j = JSON.parse(text);
          setError(j.detail ?? j.error ?? `エラー (${resp.status})`);
        } catch {
          setError(`エラー (${resp.status}): ${text.slice(0, 200)}`);
        }
        return;
      }
      const data = JSON.parse(text);
      sessionStorage.setItem("reio:extraction", JSON.stringify(data));
      router.push("/confirm");
    } catch (e) {
      setError(e instanceof Error ? e.message : "予期しないエラー");
    } finally {
      setLoading(false);
      setProgress(null);
    }
  }

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    if (loading) return;
    const f = e.dataTransfer.files?.[0];
    if (f) {
      setFile(f);
      setMode("pdf");
    }
  }

  return (
    <main className="min-h-screen bg-[var(--bg)] text-[var(--text)] flex items-start justify-center pt-16 px-4">
      <div className="w-full max-w-2xl">
        <header className="mb-8">
          <div className="font-mono text-[10px] text-[var(--accent)] tracking-widest uppercase mb-2">
            re_invest_os / v0.1
          </div>
          <h1 className="text-3xl font-bold mb-2">物件監査をはじめる</h1>
          <p className="text-[var(--text-muted)] text-sm">
            楽待 URL か販売図面 PDF
            を投入すると、30秒で「買付前に知るべきこと」が揃います。業者には何も送りません。
          </p>
        </header>

        {/* tab */}
        <div className="flex border-b border-[var(--border)] mb-6">
          {(["url", "pdf"] as ExtractionMode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`px-4 py-2 font-mono text-[11px] uppercase tracking-widest border-b-2 -mb-px transition-colors ${
                mode === m
                  ? "border-[var(--accent)] text-[var(--accent)]"
                  : "border-transparent text-[var(--text-muted)]"
              }`}
            >
              {m === "url" ? "URL" : "PDF"}
            </button>
          ))}
        </div>

        {mode === "url" ? (
          <div className="space-y-3">
            <label className="text-[10px] font-mono uppercase tracking-widest text-[var(--text-muted)]">
              楽待の物件URL
            </label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.rakumachi.jp/syuuekibukken/..."
              className="w-full bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] focus:outline-none px-3 py-2.5 font-mono text-[13px]"
              disabled={loading}
            />
            <p className="text-[11px] text-[var(--text-subtle)]">
              v1 の許可サイト: rakumachi.jp のみ。SUUMO や HOMES は次のフェーズで対応予定。
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <label className="text-[10px] font-mono uppercase tracking-widest text-[var(--text-muted)]">
              販売図面 PDF
            </label>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-[var(--border)] hover:border-[var(--accent)] transition-colors cursor-pointer py-12 text-center"
            >
              {file ? (
                <div>
                  <div className="font-mono text-sm mb-1">{file.name}</div>
                  <div className="text-[11px] text-[var(--text-muted)]">
                    {(file.size / 1024).toFixed(0)} KB
                  </div>
                </div>
              ) : (
                <div>
                  <div className="text-sm mb-1">PDF をここにドロップ</div>
                  <div className="text-[11px] text-[var(--text-muted)]">
                    またはクリックしてファイルを選択 (最大 20MB)
                  </div>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                disabled={loading}
              />
            </div>
            <p className="text-[11px] text-[var(--text-subtle)]">
              テキスト層のある PDF のみ対応。スキャン PDF は v1 では未対応。
            </p>
          </div>
        )}

        <button
          type="button"
          onClick={submit}
          disabled={loading}
          className="mt-8 w-full bg-[var(--accent)] text-[var(--bg)] py-3 font-mono font-bold text-sm uppercase tracking-widest hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? "解析中…" : "監査を開始"}
        </button>

        {progress && (
          <div className="mt-4 text-center text-[12px] text-[var(--text-muted)] font-mono">
            {progress}
          </div>
        )}

        {error && (
          <div className="mt-4 bg-[var(--surface)] border border-[var(--bad)] px-3 py-2 text-[12px] text-[var(--bad)] font-mono whitespace-pre-wrap">
            {error}
          </div>
        )}

        <details className="mt-12 text-[11px] text-[var(--text-muted)]">
          <summary className="cursor-pointer hover:text-[var(--text)]">
            プライバシーとデータの扱い
          </summary>
          <ul className="mt-2 space-y-1 list-disc list-inside">
            <li>業者・第三者にあなたの問い合わせ情報を送ることはありません</li>
            <li>個人名・連絡先は AI に送る前に自動マスクします</li>
            <li>アップロードした PDF は最大30日で自動削除されます</li>
            <li>分析結果は計算エンジンとプロンプトのバージョンが記録されます</li>
          </ul>
        </details>
      </div>
    </main>
  );
}
