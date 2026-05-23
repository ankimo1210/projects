/**
 * ウォッチリスト追加ボタン (Week 4 で実装予定 — 現状はプレースホルダ)。
 */
"use client";

import { Btn } from "../bloomberg";

export function WatchlistButton({ disabled = true }: { disabled?: boolean }) {
  return (
    <Btn variant="ghost" disabled={disabled}>
      ウォッチに追加 (準備中)
    </Btn>
  );
}
