/**
 * /login — ログイン画面 (Supabase Auth)
 * NEXT_PUBLIC_SUPABASE_URL 未設定時は「準備中」表示。
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { getSupabase } from "@/lib/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const supabase = getSupabase();

  async function handleMagicLink() {
    if (!supabase) return;
    setLoading(true);
    setError(null);
    const { error: e } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${location.origin}/auth/callback` },
    });
    setLoading(false);
    if (e) setError(e.message);
    else setSent(true);
  }

  async function handleGoogle() {
    if (!supabase) return;
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${location.origin}/auth/callback` },
    });
  }

  if (!supabase) {
    return (
      <main className="min-h-screen bg-[var(--bg)] text-[var(--text)] flex items-center justify-center">
        <div className="text-center max-w-sm">
          <div className="font-mono text-[10px] text-[var(--accent)] tracking-widest mb-4 uppercase">
            re_invest_os
          </div>
          <div className="border border-[var(--border)] bg-[var(--surface)] px-6 py-8">
            <div className="text-sm mb-4">認証機能は準備中です</div>
            <p className="text-[11px] text-[var(--text-muted)] mb-6">
              Supabase の設定が完了すると利用できます。<br />
              現在は認証なしで分析機能をお使いいただけます。
            </p>
            <Link
              href="/upload"
              className="block w-full text-center px-4 py-2 bg-[var(--accent)] text-[var(--bg)] font-mono text-[11px] uppercase tracking-widest hover:opacity-90"
            >
              ログインなしで試す →
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[var(--bg)] text-[var(--text)] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="font-mono text-[10px] text-[var(--accent)] tracking-widest mb-6 uppercase text-center">
          re_invest_os
        </div>

        <div className="border border-[var(--border)] bg-[var(--surface)] px-6 py-8">
          <h1 className="font-bold text-center mb-6">ログイン</h1>

          {sent ? (
            <div className="text-center">
              <div className="text-[var(--good)] text-sm mb-2">メールを送信しました</div>
              <p className="text-[11px] text-[var(--text-muted)]">
                {email} に届いたリンクをクリックしてください
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <button
                type="button"
                onClick={handleGoogle}
                className="w-full py-2.5 border border-[var(--border)] text-[12px] font-mono hover:bg-[var(--surface-alt)] flex items-center justify-center gap-2"
              >
                Google でログイン
              </button>

              <div className="flex items-center gap-3 text-[10px] text-[var(--text-muted)]">
                <div className="flex-1 border-t border-[var(--border)]" />
                <span>または</span>
                <div className="flex-1 border-t border-[var(--border)]" />
              </div>

              <div className="space-y-2">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="メールアドレス"
                  className="w-full bg-[var(--bg)] border border-[var(--border)] focus:border-[var(--accent)] focus:outline-none px-3 py-2 font-mono text-[12px]"
                />
                <button
                  type="button"
                  onClick={handleMagicLink}
                  disabled={loading || !email}
                  className="w-full py-2.5 bg-[var(--accent)] text-[var(--bg)] font-mono font-bold text-[11px] uppercase tracking-widest hover:opacity-90 disabled:opacity-40"
                >
                  {loading ? "送信中…" : "メールリンクを送る"}
                </button>
              </div>

              {error && (
                <p className="text-[11px] text-[var(--bad)] font-mono">{error}</p>
              )}
            </div>
          )}
        </div>

        <p className="text-center text-[11px] text-[var(--text-subtle)] mt-4">
          アカウント未登録の場合は{" "}
          <Link href="/signup" className="text-[var(--accent)] hover:underline">
            新規登録
          </Link>
        </p>

        <p className="text-center text-[11px] text-[var(--text-subtle)] mt-2">
          <Link href="/upload" className="text-[var(--text-muted)] hover:text-[var(--text)]">
            ログインなしで試す →
          </Link>
        </p>
      </div>
    </main>
  );
}
