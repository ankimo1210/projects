# Claude Code の `/compact` の内部動作 — 検証済みノート（v2）

作成 2026-08-24 / GPT レビューと一次情報照合を反映

**v1 からの主な修正: A-3 は誤りだった。** 「思考過程は保存されない」は不正確で、
正しくは「**可読なテキストは既定で省略されるが、完全な思考内容は暗号化されて
`signature` に保存されている**」。C-5 の料金倍率も誤りだった。詳細は各節に。

## 環境

- Claude Code、モデル `claude-opus-5`（1M コンテキスト）、macOS 26 / Apple Silicon
- 設定: `autoCompactEnabled: true`, `autoCompactWindow: 500000`,
  `precomputeCompactionEnabled: true`
- 調査対象: `~/.claude/projects/<project>/<session-uuid>.jsonl`

---

## A. 実測（トランスクリプトから直接取得）

### A-1. 圧縮のメタデータ ✅ 整合

`type: "system"`, `subtype: "compact_boundary"` のレコード:

```json
{
  "trigger": "manual",
  "preTokens": 233376,
  "postTokens": 8125,
  "cumulativeDroppedTokens": 225251,
  "durationMs": 109276,
  "preservedSegment": { "headUuid": "...", "anchorUuid": "...", "tailUuid": "..." },
  "preCompactDiscoveredTools": [ /* MCP ツール10件 */ ],
  "preservedMessages": /* キーの存在を確認 */
}
```

→ **233,376 → 8,125 トークン（96.52% 削減）、所要 109.276 秒。**

### A-2. 要約の構造 ⚠️ 一般化はできない

`isCompactSummary: true` のレコード。本文 12,761 文字。**この1回の観測では**
以下9セクションだった。バージョンや部分要約、カスタム指示で変わりうるため、
「常に9固定」とは言えない。

```
1. Primary Request and Intent    6. All user messages
2. Key Technical Concepts        7. Pending Tasks
3. Files and Code Sections       8. Current Work
4. Errors and fixes              9. Optional Next Step
5. Problem Solving
```

要約末尾に圧縮前トランスクリプトの絶対パスが埋め込まれている。

### A-3. thinking ブロック 🔴 v1 は誤り。以下が正しい

**測定値**（v1 は最初の2ブロックしか見ておらず範囲を誤記していた）:

```
thinking ブロック: 170個（redacted_thinking: 0個）
  thinking  = ""                     ← 170個すべて空
  signature = 384〜13,436 文字        ← 可変長。170個中160種類の長さ
```

**正しい解釈:**

`signature` の長さが内容に比例して変動することは、そこにデータが入っている
ことを示す。公式ドキュメントが裏付けている。

> **"Full thinking content is encrypted and returned in the `signature` field
> on each thinking block."**
> "The `signature` field is opaque: don't interpret or parse it."
> — [Thinking encryption](https://platform.claude.com/docs/en/build-with-claude/thinking#thinking-encryption)

`thinking` が空である理由も特定できた。**`display: "omitted"` が Opus 5 の
既定値**であるため。

> `"omitted"`: thinking blocks are returned with an empty `thinking` field.
> The `signature` field still carries the encrypted full thinking for
> multi-turn continuity. **This is the default on Claude Fable 5, Claude
> Mythos 5, Claude Opus 5, Claude Sonnet 5, Claude Opus 4.8, Claude Opus 4.7**
> — [Controlling thinking display](https://platform.claude.com/docs/en/build-with-claude/thinking#controlling-thinking-display)

したがって:

| | |
|---|---|
| 保存されているか | **されている**。完全な思考内容が暗号化されて `signature` に |
| 人間が読めるか | **読めない**。opaque と明記され、復号はサーバ側のみ |
| `display: "summarized"` にすれば読めるか | 読めるのは**要約**であって raw CoT ではない |

> "No `display` setting returns the raw chain of thought."

**結論:** 「保存されていない」も「後から読める」も両方誤り。
正しくは「**保存されているが、どの設定でも人間が生の思考を読むことはできない**」。
なお `display: "omitted"` は課金を減らさない（レイテンシのみ改善）。

### A-4. その他の実測値

- `isCompactSummary` レコードに **`model` フィールドが存在しない**
- レコード種別: assistant 433 / user 236 / attachment 205 /
  file-history-snapshot 26 ほか
- ツール呼び出しと**その実行結果**は保存されている
- `~/.claude/projects/`: jsonl 21ファイル / 13MB / 最古 2026-07-29
- `~/.claude/settings.json` に `cleanupPeriodDays` の記載なし（既定 30日が適用）

---

## B. 推論

**B-1. ⚠️ 根拠不足（GPT 指摘を受諾）**

「`6. All user messages` があるため圧縮後トークン数が単調増加する」と述べたが、
**確立していない**。圧縮は損失を伴う再要約であり、過去のユーザー発言が毎回
原文のまま維持される保証はない。`cumulativeDroppedTokens` は「累積破棄量」で
あって保持量ではないため、裏付けにならない。観測できた圧縮は1回のみ。

言えるのは「この1回では section 6 に全ユーザー発言が原文で入っていた」まで。

**B-2. ✅ 概ね正しい**

圧縮は同じ履歴全体に要約指示を加えた単一リクエスト。したがって要約モデルは
圧縮前コンテキスト全体を収容できる必要がある。

- Opus 5 / Sonnet 5: 1M → `autoCompactWindow: 500000` が有効
- Haiku 4.5: 200k → 500k の履歴は処理不可能。設定値はモデル実上限で切り詰められる
- 実際には要約の出力分の余裕も要る

**B-3. ✅ 正しい**

キャッシュ失効後の1手目は全履歴を未キャッシュ入力として再処理する。窓を絞る
ことは失効の防止ではなく、**失効時の最大入力量とコストの上限を下げる**。

---

## C. 未確認だった点 → 決着

| | 結論 | 根拠 |
|---|---|---|
| C-1 圧縮を行うモデル | 通常はセッションのアクティブモデル。キャッシュはモデル別に分かれるため、暖かいキャッシュを使う通常経路では同一モデルになる。ただしフォールバック経路は存在し、JSONL に `model` がない以上この1回が Opus 5 だったとは証明できない | GPT。JSONL では確認不能 |
| C-2 圧縮専用モデルの設定 | **存在しない**。`compactModel` 相当の公開設定はない。`/model` で主モデルを変えると間接的に変わる | GPT |
| C-3 `cleanupPeriodDays` 既定 | **30日** | 公式仕様 |
| C-4 コンテキスト上限 | Haiku 4.5 = **200k** / Sonnet 5 = **1M** / Opus 5 = **1M** | 料金表「Claude 4.6 and later models include the full 1M token context window at standard pricing」 |
| C-5 キャッシュ料金倍率 | 🔴 **v1 は誤り**。下表参照 | 公式料金表 |

### C-5 の訂正

| Cache operation | Multiplier | Duration |
|---|---|---|
| 5-minute cache write | 1.25x base input | 5分 |
| **1-hour cache write** | **2x base input** | 1時間 |
| Cache read (hit) | 0.1x base input | — |

v1 は「書き込み ≈ 1.25倍」と書いたが、これは**5分TTLの値**。Claude の
サブスクリプション会話は通常1時間TTLなので **2倍**が正しい。「TTLは1時間」と
「書き込み1.25倍」は同時に成立しない。

> "caching pays off after one cache read for the 5-minute duration (1.25x
> write), or after two cache reads for the 1-hour duration (2x write)."
> — [Pricing](https://platform.claude.com/docs/en/about-claude/pricing#prompt-caching)

### 補足：1M に長コンテキスト割増はない

> "Claude 4.6 and later models include the full 1M token context window at
> standard pricing. (A 900k-token request is billed at the same per-token
> rate as a 9k-token request.)"

つまり `autoCompactWindow` を絞る動機は**単価の割増ではなく、キャッシュ失効時の
再処理量**にある。B-3 の根拠はこれで補強される。

---

## D. 再現用コマンド

```bash
f=~/.claude/projects/<project>/<session-uuid>.jsonl

# 圧縮メタデータ
python3 -c "
import json
for l in open('$f'):
    d = json.loads(l)
    if d.get('subtype') == 'compact_boundary':
        print(json.dumps(d['compactMetadata'], indent=2))
"

# thinking / redacted_thinking と signature 長の分布
python3 -c "
import json, collections, statistics
t = collections.Counter(); sigs = []
for l in open('$f'):
    for p in (json.loads(l).get('message') or {}).get('content') or []:
        if isinstance(p, dict) and 'thinking' in str(p.get('type', '')):
            t[p['type']] += 1
            if p.get('type') == 'thinking': sigs.append(len(p.get('signature', '')))
print(t.most_common())
print(f'sig: n={len(sigs)} min={min(sigs)} max={max(sigs)} uniq={len(set(sigs))}')
"
```

`signature` が固定長なら純粋な署名、可変長なら内容依存のデータを含む
（実測では可変長で、公式仕様どおり暗号化された思考内容だった）。

---

## 出典

- [Thinking](https://platform.claude.com/docs/en/build-with-claude/thinking) — encryption / display
- [Pricing](https://platform.claude.com/docs/en/about-claude/pricing) — キャッシュ倍率、1M 標準価格
- [Extended thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking)

## 残る未確認

- 圧縮を行った実際のモデル（JSONL に記録がなく、原理的に特定不能）
- Claude Code の `showThinkingSummaries` 設定の挙動（GPT が言及。当方未検証）
- B-1（圧縮後トークン数の推移）— 複数回の圧縮を観測すれば実測可能
