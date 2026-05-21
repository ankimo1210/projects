/**
 * /signup — 新規登録画面 (Supabase Auth)
 * Magic Link 方式 (メール確認)。
 */
"use client";

import Link from "next/link";

export default function SignupPage() {
  return (
    <main className="min-h-screen bg-[var(--bg)] text-[var(--text)] flex items-center justify-center px-4">
      <div className="w-full max-w-sm text-center">
        <div className="font-mono text-[10px] text-[var(--accent)] tracking-widest mb-6 uppercase">
          re_invest_os
        </div>
        <div className="border border-[var(--border)] bg-[var(--surface)] px-6 py-8">
          <h1 className="font-bold mb-4">新規登録</h1>
          <p className="text-[12px] text-[var(--text-muted)] mb-6">
            登録は<Link href="/login" className="text-[var(--accent)] hover:underline">ログインページ</Link>から
            メールアドレスを入力するだけです。<br />
            パスワード不要のマジックリンク方式を採用しています。
          </p>
          <Link
            href="/login"
            className="block w-full text-center px-4 py-2.5 bg-[var(--accent)] text-[var(--bg)] font-mono font-bold text-[11px] uppercase tracking-widest hover:opacity-90"
          >
            メールアドレスで登録 →
          </Link>
        </div>
        <p className="text-[11px] text-[var(--text-subtle)] mt-4">
          <Link href="/terms" className="hover:underline">利用規約</Link>
          {" "}・{" "}
          <Link href="/privacy" className="hover:underline">プライバシーポリシー</Link>
          に同意の上ご登録ください
        </p>
      </div>
    </main>
  );
}
