import type { Metadata } from "next";
import { DashboardShell } from "@/components/dashboard-shell";
import "./globals.css";
export const metadata: Metadata = {
  title: { default: "概要 | Health Archive", template: "%s | Health Archive" },
  description: "ローカルの健康記録を閲覧する個人用ダッシュボード",
  robots: { index: false, follow: false },
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja" suppressHydrationWarning>
      <body>
        <DashboardShell>{children}</DashboardShell>
      </body>
    </html>
  );
}
