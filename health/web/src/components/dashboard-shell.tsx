"use client";
// Sidebar/header/inset composition adapted from Studio Admin, commit in THIRD_PARTY_NOTICES.md.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import {
  Activity,
  ArrowUpRight,
  Heart,
  Home,
  Lightbulb,
  LockKeyhole,
  Moon,
  Sun,
  Database,
  Footprints,
  Scale,
  RefreshCw,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { TooltipProvider } from "@/components/ui/tooltip";
import { PeriodProvider, PeriodSelector } from "./period-provider";
import { DataProvider, useMeta } from "./data-provider";
import { statusLabel } from "@/lib/presentation";
export const routes = [
  {
    path: "/",
    label: "概要",
    en: "OVERVIEW",
    icon: Home,
    description: "日々の記録から、からだの今を見渡す。",
  },
  {
    path: "/insights/",
    label: "気づき",
    en: "INSIGHTS",
    icon: Lightbulb,
    description: "いつもの自分との違いと、日々のつながり。",
  },
  {
    path: "/sleep/",
    label: "睡眠",
    en: "SLEEP",
    icon: Moon,
    description: "眠りの深さと、毎晩のリズムを振り返る。",
  },
  {
    path: "/activity/",
    label: "活動",
    en: "ACTIVITY",
    icon: Footprints,
    description: "歩いた距離、動いた時間。日常の積み重ね。",
  },
  {
    path: "/heart/",
    label: "心拍",
    en: "HEART",
    icon: Heart,
    description: "安静時から一日の細かな変化まで。",
  },
  {
    path: "/body/",
    label: "身体",
    en: "BODY",
    icon: Scale,
    description: "からだの指標を、それぞれの単位で。",
  },
  {
    path: "/inventory/",
    label: "データ棚卸し",
    en: "DATA INVENTORY",
    icon: Database,
    description: "保存できた記録と、まだ確認できていない範囲。",
  },
];
function Navigation() {
  const path = usePathname();
  const { setOpenMobile } = useSidebar();
  return (
    <Sidebar variant="inset" collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild size="lg">
              <Link href="/" prefetch={false}>
                <div className="brand-icon">
                  <Activity />
                </div>
                <div className="brand-text">
                  <strong>Health Archive</strong>
                  <span>PERSONAL / LOCAL</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>あなたの記録</SidebarGroupLabel>
          <SidebarMenu>
            {routes.map(({ path: href, label, icon: Icon }) => (
              <SidebarMenuItem key={href}>
                <SidebarMenuButton
                  asChild
                  tooltip={label}
                  isActive={path.replace(/\/$/, "") === href.replace(/\/$/, "")}
                >
                  <Link
                    prefetch={false}
                    href={href}
                    onClick={() => setOpenMobile(false)}
                    aria-current={
                      path.replace(/\/$/, "") === href.replace(/\/$/, "")
                        ? "page"
                        : undefined
                    }
                  >
                    <Icon />
                    <span>{label}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <div className="local-note group-data-[collapsible=icon]:hidden">
          <LockKeyhole size={16} />
          <strong>自分の記録を、自分の手元に。</strong>
          <p>ローカル保存データの閲覧専用画面</p>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
function Chrome({ children }: { children: ReactNode }) {
  const path = usePathname();
  const route =
    routes.find((r) => r.path.replace(/\/$/, "") === path.replace(/\/$/, "")) ??
    routes[0];
  const { meta, error, reload, loading } = useMeta();
  const [dark, setDark] = useState(false);
  const [now] = useState(() => Date.now());
  useEffect(() => {
    const saved = localStorage.getItem("health-theme");
    const dark = saved
      ? saved === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.classList.toggle("dark", dark);
    requestAnimationFrame(() => setDark(dark));
  }, []);
  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("health-theme", next ? "dark" : "light");
  }
  return (
    <SidebarProvider>
      <a className="skip-link" href="#main">
        本文へ移動
      </a>
      <Navigation />
      <SidebarInset className="min-w-0 border border-border">
        <header className="topbar">
          <div className="flex items-center gap-3">
            <SidebarTrigger aria-label="サイドバーを切り替え" />
            <span className="topbar-divider" />
            <span className="text-sm">
              マイヘルス{" "}
              <span className="text-muted-foreground">/ {route.label}</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="local-badge">
              <span />
              ローカル
            </span>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              aria-label={
                dark ? "ライトモードに切り替え" : "ダークモードに切り替え"
              }
            >
              {dark ? <Sun /> : <Moon />}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              disabled={loading}
              onClick={reload}
              aria-label="エクスポートを再読み込み"
            >
              <RefreshCw className={loading ? "animate-spin" : ""} />
            </Button>
          </div>
        </header>
        <main id="main" className="page-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">{route.en}</div>
              <h1>{route.label}</h1>
              <p>{route.description}</p>
            </div>
            <PeriodSelector />
          </div>
          <div className="freshness">
            <span>
              {meta
                ? `書き出し ${new Date(meta.generatedAt).toLocaleString("ja-JP")}`
                : loading
                  ? "スナップショットを確認中"
                  : error
                    ? "エクスポート未読込"
                    : "未接続"}
            </span>
            {meta && (
              <>
                <span>
                  原本:{" "}
                  {statusLabel[meta.freshness.archiveStatus] ??
                    meta.freshness.archiveStatus}
                </span>
                <span>
                  表示:{" "}
                  {statusLabel[meta.freshness.projectionStatus] ??
                    meta.freshness.projectionStatus}
                </span>
              </>
            )}
          </div>
          {meta && meta.freshness.archiveStatus !== "complete" && (
            <Link
              href="/inventory/"
              className="coverage-notice"
              prefetch={false}
            >
              <Database size={16} />
              <span>原本の取得には未確認・未完了の範囲があります。</span>
              <ArrowUpRight size={16} />
            </Link>
          )}
          {meta && now - Date.parse(meta.generatedAt) > 7 * 86400000 && (
            <p className="stale-notice">
              書き出しから7日以上経過しています。測定日と取得状況を確認してください。
            </p>
          )}
          {children}
          <footer className="page-footer">
            <span>HEALTH ARCHIVE</span>
            <span>値の日付と書き出し日時は異なります。</span>
          </footer>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <TooltipProvider>
      <PeriodProvider>
        <DataProvider>
          <Chrome>{children}</Chrome>
        </DataProvider>
      </PeriodProvider>
    </TooltipProvider>
  );
}
