# Stochastic — 不確かな世界の微分方程式

ランダムウォークから Itô 計算、PDE、Brownian 運動を超えるノイズ、数値計算法、
金融・自然科学・モデリング実務までを、数値実験と一緒に学ぶ全47章の
インタラクティブ教科書です。

## 全47章の構成

| Part | 章 | 収録内容 |
|---|---:|---|
| I · 離散から連続へ | 1–4 | SDE の必要性、ランダムウォーク、Brownian 運動、経路・分布・情報 |
| II · 通常の微積分が壊れる理由 | 5–8 | 経路の粗さ、二次変分、確率積分、Itô の公式 |
| III · 基本 SDE モデル | 9–14 | ドリフトと拡散、算術・幾何 Brownian、OU、CIR、多次元相関 |
| IV · 経路から分布と PDE へ | 15–19 | 生成作用素、後退方程式、Fokker–Planck、Feynman–Kac、初到達 |
| V · Brownian 運動を超えるノイズ | 20–25 | Brownian 極限、Poisson・Lévy、有色ノイズ、fractional Brownian、Hawkes |
| VI · 数値計算法 | 26–30 | Euler–Maruyama、強・弱収束、Milstein、Monte Carlo、推定と潜在状態 |
| VII · 金融モデリング | 31–38 | 予測可能性、マルチンゲール、P と Q、動的ヘッジ、ボラティリティ、金利、信用 |
| VIII · 金融以外の応用 | 39–44 | Langevin 力学、化学反応、個体群、感染症、神経科学、フィルタリング |
| IX · モデリング実務 | 45–47 | モデル選択、モデル批判、SDE が主張すること・しないこと |

## インタラクティブ可視化

章ごとの Canvas 実験では、パラメータを変えながら次の比較を行えます。

- 結合した経路、横断面分布、解析値、Monte Carlo 指標の連動
- Brownian の粗さ・二次変分・Itô 補正と、経路法・PDE 法の照合
- ジャンプ、重い裾、有色ノイズ、長期記憶、自己励起イベントの比較
- Euler・Milstein の収束、Monte Carlo 標本誤差、パラメータ・状態推定
- 実世界測度 P とリスク中立測度 Q、動的ヘッジ、ボラティリティ・金利・信用モデル
- 物理・化学・生態・感染症・神経・追跡問題と、モデル選択・残差診断

乱数実験は seed 付きで再現でき、外部 API や実行時ダウンロードを必要としません。

## 教材と実装

本文は次のモジュールに構造化しています。

- [`content/chapters.ts`](content/chapters.ts): 第1–19章、第26章、第33章、型定義、用語集
- [`content/chapters-part-v-vi.ts`](content/chapters-part-v-vi.ts): 第20–25章、第27–30章
- [`content/chapters-part-vii.ts`](content/chapters-part-vii.ts): 第31・32章、第34–38章
- [`content/chapters-part-viii-ix.ts`](content/chapters-part-viii-ix.ts): 第39–47章

章表示と基本実験は [`app/sde-textbook.tsx`](app/sde-textbook.tsx)、ノイズ・数値法・金融の比較実験は
[`app/extended-labs.ts`](app/extended-labs.ts)、自然科学・モデリング実務の実験は
[`app/application-labs.ts`](app/application-labs.ts) に実装しています。

## ローカル実行

Node.js 22.13 以上が必要です。

```bash
npm ci
npm run dev
```

本番相当の検証:

```bash
npm run lint
npm run typecheck
npm test
```

`npm test` は production build のあと、レンダリング回帰テストと数値回帰テストを実行します
(計 12 本)。数値側は `app/stochastic-models.mjs` に切り出した純関数
(Feynman–Kac の閉形式・後退方程式・Black–Scholes・α-stable・fGn 共分散・Vasicek 債券価格)を、
独立した求積や解析式と突き合わせている。

## 設計原則

- 直観 → 数値実験 → 定義・式 → 限界 → 演習の順で読む
- 解析式とシミュレーションを明確に区別する
- `(dW)²=dt` を点ごとの代数的等式として扱わない
- (P) を予測、(Q) を無裁定価格付けのための測度として区別する
- Canvas、HTML、CSS のみで図を描き、静的配信後も自己完結して動く
- キーボード操作、reduced motion、dark mode、印刷表示に対応する
