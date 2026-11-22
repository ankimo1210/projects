# Sauna Compact V10 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for the parent work; the user-designated persistent Fable/high conversation authors the new model sources.

**Goal:** 170㎡・24人の比較版をFableと照合し、元案を保持して実画像/実3Dを納品する。

**Architecture:** 新規配置JSONと独立Blenderソースを既存の素材/メッシュヘルパーで作る。親がソースを監査し、新ルートに生成・検査・GPU描画・GLB出力する。未取得条件をモデルで保証しない。

**Tech Stack:** Python stdlib、既存Blender 5.2/Cycles OPTIX、既存three.js Viewer。

**Spec:** ../../V10_BRIEF.md

## Global Constraints

- 同じFable会話ID、high。旧モデル/素材/会話/hand off ZIPを削除/上書きしない。
- 原型170㎡、24人目標、2サ室/2槽、16休憩/4シャワー/30ロッカー。費用・許可・メーカー等の成立は未確認。
- ソースは専用worktree、生成物はcanonical fable-v10/、上限1GiB。既存依存のみ。
- FableはRead/Write/Editのみ。拒否された操作を迂回しない。親は新規ソースを監査後に独立実行。

## Review Focus

- 壁/通路/浴槽水面の面積重複 → 区画座標の集計と相互重複検査。
- 中央寄せストーブで演者/着席/出入りが干渉 → 仮人体/演者円とメッシュ境界検査。
- 浅槽でも支持・頭上不足 → 水面/底/支持の高さと仮断面を検査。
- 16席満席やイベント冷槽待機で閉塞 → 通路外の待機と退路を模型/平面で照合。
- 画像/GLBの版差・欠落素材・見えないモデル → 保存SHA・依存検査・親CUAで読込/UI確認。

### Task 1: 配置・新規モデルソース

**Files:** docs/V10_BRIEF.md、plan/compact_v10.json、blender/compact_v10.py、docs/V10_DESIGN.md、scripts/run_fable_v10.py。

- [x] 旧成果のSHAと保存会話の状態を記録し、Fableを重複なく再開。
- [x] Fableが2室2槽の区画/扉/席/動線と条件付き断面を設計し、新規ソースだけを作成。
- [x] 親が仕様との差、危険な書込/旧版変更、座標と生成コマンドを監査。

### Task 2: 実モデルと検証

**Files:** 新規compactソース・wrapper・必要な検証/テスト。

- [x] 面積/高さ/水量/通路/席の独立確認で不足を先に特定し、修正後に再確認。
- [x] Blender build→保存後再読込verify、必要な修正を新規ソースだけへ反映。
- [x] 最小試写で構図・照明・身体干渉を確認。既知問題を記録。

### Task 3: 最終画像・GLB・表示

**Files:** fable-v10/model,renders,diagrams,viewer,verification、viewer-v10/。

- [x] 同じ保存モデルから本番画像、GLB、平面/断面を出力。
- [x] Viewerに全体/室内の視点と人体/天井/検討線切替を用意し、親がCUAで実表示確認。
- [x] 全manifest/旧版不変/会話保存/容量を照合し、README/STATUSと設計メモへ結果/残課題を更新。

実行はユーザー指定により開始する。新規承諾/採用案決定/発注をこの比較版の生成から推定しない。

完了: 2026-11-16。画像/実3D/表示/保全の概念比較成果まで。サ室前0.756m/休憩不足/構造等の留保を残し、施工・費用成立は完了条件に含めない。[結果](../../V10_PARENT_REVIEW.md)。
