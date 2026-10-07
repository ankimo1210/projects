# 残り45節の軽量受入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ch29–37の残45節を原典要件・検証範囲・不足入力とともに判定し、全306節の受入状態を確定する。

**Architecture:** 旧261受入を凍結し、fast-v1の新recipe/adapterと章別補足教材を追加する。P7の新private3モジュール/10testを開発branch b8ea5695から取り込み、§33.2/36.4は回収資料から新private2モジュールで補完する。既存共有codeは変更しない。原典未指定の株価/契約条件は逆合わせせず、入力のない原典結果と検証可能な式・手順を区別する。

**Tech Stack:** WSL Ubuntu、共通Python venv、既存pytest/NumPy/SciPy/MarkdownIt/Playwright/Chromium。production依存/公開API追加なし。

**Spec:** docs/FAST_ACCEPTANCE_GUIDE.md、docs/prep/sections/ch29.md〜ch37.md、P3/P7_STATUS.md。

## Global Constraints

- 基点0d07def7、codex/johnhull-acceptanceでlocal作業。main統合/remote push/公開は別工程。
- 旧261 accepted行・対象外261行の完全一致。旧recipe/core/教材/numerical sourceを変更しない。
- 全要件・時点・通貨/元本/vol単位を保持。合成検証を原典価格の再現としない。
- 数値/test/recipe/教材/配布物を指紋固定。件数testと進捗文書は過去数値sourceへpinしない。
- 全suite/全Book/別幅/全節画像/二重復元は承認済みfast-v1で省略。

## Review Focus

- §33.2のmeasure/tenor/resetと指定されないflexicap strike、§36.4の原典未指定parameterをverifiedへ紛れ込ませない。
- 金利θ/σの単位、収束格子/終端1日規約、market fitと合成curveを区別する。
- commodity futures較正に割引state priceを使わない。日次温度/payoffとprice測度を分ける。
- 投資optionの支払/行使時点、共同4状態/希薄化/倒産を区別する。
- adapterとrunnerのsource集合を一致させ、旧namespace/provenanceと261判定を保持する。

## Tasks

- [x] Ch29–34の29節の本文・要求分類・節別test/制限・補足教材をそろえる。
- [x] Ch35–37の16節の新private codeを最小範囲で取り込み、本文・要求分類・補足教材と対象検証をそろえる。
- [x] §33.2/§36.4の原典と既存計算を調査し、不足入力を正直に扱える最終判定を記録する。
- [x] 新recipe/adapter/guardを作り、fresh対象testと45節browser/代表9画像を検証する。
- [x] 独立レビューの重要指摘を解決し、native台帳/既存261行/件数/summaryを検証する。
- [x] ローカルcommit後にread-only既存/新証跡とtracked releaseを確認し、全体結果を報告する。

## 完了確認 — 2026-10-08

実装commit `5a2b72c9`。対象389 tests・台帳41 tests、45節/149要求・598数式/22表・代表9画像PASS。
独立レビューC/I/Minor0、旧261行と全対象外261行を保持。commit後の新45節と旧36/54/58節の
read-only verify、全306 accepted artifacts、証跡鮮度、strict tracked release PASS。原典未指定価格の
再現・main統合・公開は宣言した受入範囲と区別する。数値・画面証跡をcommit後に再生成していない。
