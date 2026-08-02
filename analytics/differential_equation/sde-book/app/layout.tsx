import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import "./globals.css";

const title = "Stochastic — 不確かな世界の微分方程式";
const description =
  "ランダムウォークから Itô 計算、SDE モデル、Fokker–Planck 方程式、数値計算、測度変更までを実験で学ぶインタラクティブ教科書。";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost";
  const protocol =
    requestHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  let imageUrl = "http://localhost/og.png";
  try {
    imageUrl = new URL("/og.png", `${protocol}://${host}`).toString();
  } catch {
    // Keep metadata valid even when a development proxy supplies an invalid host.
  }

  return {
    title,
    description,
    applicationName: "Stochastic",
    openGraph: {
      type: "website",
      title,
      description,
      locale: "ja_JP",
      images: [
        {
          url: imageUrl,
          width: 1731,
          height: 909,
          alt: "ランダムウォークからブラウン運動、Itô 計算へ進む確率微分方程式教材",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [imageUrl],
    },
  };
}

export const viewport: Viewport = {
  colorScheme: "light dark",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4f3ed" },
    { media: "(prefers-color-scheme: dark)", color: "#0f191c" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
