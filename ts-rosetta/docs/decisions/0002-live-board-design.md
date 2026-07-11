# 0002 — Live-board reactivity comparison design

Status: Accepted (2026-07-10)

## Context

トレーディング UI 検討の帰結として「フレームワーク差が実際に出るのは、多数の
DOM 要素を自前で高頻度更新する場面だけ」を実測で示すモジュールを追加した。
5 実装（React naive / React optimized / Vue / Angular / Solid）が同一の
ティックストリームを受け、リアクティビティ配線だけを変える。

## Decision

- **Solid を追加（Svelte ではなく）**: JSX 構文が React とほぼ同一のまま
  実行モデルだけが変わるため、「構文 ≠ 実行モデル」を最小差分で見せられる。
  Svelte はテンプレート構文ごと変わり、差の原因が二重になる。
- **共有エンジンはシード固定・fraction 0.1・setInterval 駆動**。
  詰まると tick が間引かれ upd/s が落ちる＝スループット指標を兼ねる。
  0.3→0.1 にしたのは naive の増幅率（rows×ticks ÷ touched）を現実的な
  板の更新密度で 10 倍にするため。
- **work/s はフレームワークごとに意味が違う**（React=行レンダー、Vue=行更新、
  Angular=行 CD チェック、Solid=last セル effect）。「行を触った回数」として
  比較可能に揃え、定義差は docs に明記。Solid のカウントは dir でなく
  **last のテキスト effect** に載せる（dir は半分しか変化せず過少計上になる）。
- **セルの点滅はやらない**（CSS アニメ再トリガや timeout は各 FW の追加状態を
  生み、計測を汚す）。dir による色分けのみ。
- **fps が主役にならないことを受け入れる**: 計測の結果、崩壊時の律速は
  巨大テーブルの layout（共通コスト）で、fps はフレームワークを分離しない。
  無理に行を人工的に重くして「naive が崩れる」画を作るのは不誠実なのでやらず、
  work/s（CPU 予算）と「仮想化が本命」を結論に据えた。
- **CPU 4x スロットリング（CDP）** を計測構成に含め、弱いデバイス相当でも
  fps が分離しないことまで含めて記録した。
- React だけ naive/optimized の 2 変種を持つ（罠→対策の再現が目玉のため）。
  Vue/Angular/Solid は各エコシステムの推奨形のみ。

## Consequences

- 「リアクティビティの差 = fps の差」という素朴な期待は本ラボでは**否定**され、
  「CPU 予算（work/s）10.6 倍の差 + fps を守るのは仮想化」が公式の結論になった。
- 行コンポーネントが重い実アプリでは fps に直撃し得る — その検証は今後
  行を意図的に重くする実験を足す場合の拡張ポイント（人工ベンチになる自覚を持つこと）。
- Svelte / Vue Vapor / React Compiler を足す場合も同じエンジン・同じ指標に
  載せるだけで比較に参加できる。
