# TypeScript vs JavaScript — 同じバグの運命の違い

`packages/core/js-vs-ts/` に**同じバグを仕込んだ同じ関数**が 2 つある。
割引計算に `price: '1200'`（文字列）と `rate: '10%'` を渡してしまう誤用。

## TypeScript 版: コンパイル時に止まる

```bash
$ pnpm --filter @rosetta/core demo:ts   # = tsc -p js-vs-ts
js-vs-ts/discount.ts(15,45): error TS2322: Type 'string' is not assignable to type 'number'.
```

**コードは 1 行も実行されていない。** エディタ上では書いた瞬間に赤線が出る。

## JavaScript 版: 実行時まで誰も気づかない

```bash
$ pnpm --filter @rosetta/core demo:js   # = node js-vs-ts/discount.js
total: NaN
    console.log(item.prise.toFixed(2)); // typo: prise
                            ^
TypeError: Cannot read properties of undefined (reading 'toFixed')
```

2 種類の失敗が起きている:

1. **静かなゴミ**: `'1200' * (1 - '10%')` → `NaN`。エラーにすらならず
   `total: NaN` が表示される。本番なら請求書に NaN が印字されるまで気づかない。
2. **実行時クラッシュ**: プロパティ名の typo（`prise`）はその行が実行されて
   初めて `TypeError` で落ちる。テストで通らなかったパスなら本番で落ちる。

## 要点

| | TypeScript | JavaScript |
|---|---|---|
| 型の誤用 | コンパイルエラー（実行前） | 実行時に NaN / TypeError、または沈黙 |
| typo | エディタで即赤線 | 実行するまで不明 |
| 実行 | 直接は実行できない。**JS に変換して**ブラウザ / Node で動かす | そのまま動く |
| コスト | 型を書く手間 + ビルド工程 | なし（そのぶんバグは実行時へ） |

このリポジトリの全コードが TS で書かれているのはこのため。ブラウザや Node.js が
実際に実行しているのは、tsc / Vite / esbuild が変換した **JavaScript** である
（`packages/core/dist/cjs/` を見ると変換結果が読める）。
