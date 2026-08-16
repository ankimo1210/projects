# labor_ai_quadrant

**人手不足の深刻度 × AI代替可能性** の 4象限フレームワーク（日本の上場企業）。

```
                  AI代替可能性 ↑
   ┌──────────────────────┬──────────────────────┐
   │ AI増益                │ AI解放  ★            │
   │ 人手不足ではないが     │ 人手不足が深刻で、    │
   │ AI代替余地は大きい     │ かつAIで代替できる    │
   │ → マージン改善         │ → 供給制約が外れる    │
   ├──────────────────────┼──────────────────────┤
   │ 低感応                │ 人手依存              │
   │ どちらも低い          │ 人手不足は深刻だが     │
   │ → この枠組みの対象外   │ AIでは解けない        │
   │                      │ → 賃上げ・自動化設備   │
   └──────────────────────┴──────────────────────┘
                              人手不足の深刻度 →
```

**右上（AI解放）に入る企業だけが、人手不足という供給制約を賃上げ以外の手段で外せる。**
このプロジェクトは、その右上を東証33業種と個別銘柄のレベルで特定する。

> 📦 [projects monorepo](../README.md) の uv workspace メンバー。`.venv` はリポジトリルート共有。

---

## この枠組みの核心

**2軸は負の相関を持ちやすい。** そこがこのフレームワークの情報源になっている。

- 人手不足が最も深刻な労働 — 建設・介護・運転・保安 — は、**AIが最も苦手とする身体労働**
- AIが最も得意な労働 — 事務・審査・コーディング — は、**必ずしも人手不足ではない**
  （事務職の有効求人倍率は 0.5倍を下回る一方、建設躯体工事は 9倍前後）

だから右上は本質的に狭い。「人手不足だからAI」という素朴な話の大半は、実際には
右下（人手依存）か左上（AI増益）に落ちる。右上に入ることが情報になる。

現行の既定設定での業種の落ち方:

| 象限 | 業種 |
|---|---|
| **AI解放** (9) | 情報・通信業、サービス業、小売業、不動産業、その他金融業、卸売業、金属製品、機械、ガラス・土石製品 |
| **人手依存** (7) | 建設業、陸運業、倉庫・運輸関連業、水産・農林業、食料品、海運業、空運業 |
| **AI増益** (7) | 銀行業、証券、保険業、電気機器、その他製品、ゴム製品、繊維製品 |
| **低感応** (10) | 化学、医薬品、鉄鋼、非鉄金属、輸送用機器、精密機器、パルプ・紙、石油・石炭製品、鉱業、電気・ガス業 |

建設業は人手不足スコア **100 / AI代替可能性 3**、陸運業は **94 / 0**。
どちらもこの枠組みでは「AIでは救われない」側にはっきり分離される。
逆に銀行業は **2 / 91** で、人手不足ではないがAI余地は最大級 — 成長ではなくコストの話になる。

---

## クイックスタート

```bash
# ワークスペースルートで一括インストール
cd ~/projects && make install          # = uv sync --all-packages

# 33業種のスコア一覧
uv run --no-sync python -m labor_ai_quadrant sectors

# 右上象限（AI解放）の銘柄ランキング
uv run --no-sync python -m labor_ai_quadrant top --level company -n 25

# オフラインHTMLレポート（4象限マップ + ランキング + 感応度）
uv run --no-sync python -m labor_ai_quadrant build --out reports/quadrant.html
```

Python から:

```python
from labor_ai_quadrant import sector_frame, company_frame, top_right, Config

sectors = sector_frame()                     # 33業種 × 2軸 + 象限
companies = company_frame()                  # 個別銘柄に展開
top_right(companies, 20)                     # 右上象限のランキング

# 感応度: 「AI」を生成AIだけと見るか、ロボ/自動運転まで含めるか
sector_frame(Config(robotics_weight=0.0))    # LLMのみ
sector_frame(Config(robotics_weight=0.6))    # ロボ・自動運転込み
```

---

## 2つの軸

### X軸 — 人手不足の深刻度

公表労働統計の6指標を33業種横断で z 化し、重み付き合成して 0-100 に相対化する。

| 指標 | 重み | 出典 |
|---|---|---|
| 欠員率 | 0.30 | 厚労省「雇用動向調査」産業別 |
| 有効求人倍率 | 0.25 | 厚労省「一般職業紹介状況」職業別 |
| 正社員不足割合 | 0.25 | 帝国データバンク「人手不足に対する企業の動向調査」 |
| 55歳以上就業者比率 | 0.10 | 総務省「労働力調査」 |
| 離職率 | 0.05 | 厚労省「雇用動向調査」 |
| 所定外労働時間 | 0.05 | 厚労省「毎月勤労統計調査」 |

上位2指標が「いま採れていない」ことの直接的な測度、残りは将来圧力と不足の帰結。

### Y軸 — AI代替可能性

**業種の職業構成比 × 職業別のAI代替ポテンシャル** の内積。ハンドウェーブではなく計算する。

```
sector_ai_share = Σ_職業 ( 構成比[業種][職業] × ポテンシャル[職業] ) × (1 - 規制ドラッグ[業種])
ポテンシャル[職業] = llm_potential × (1 - w) + phys_potential × w      # w = robotics_weight
```

職業別ポテンシャルは **生成AI(LLM)成分** と **物理自動化(ロボ・自動運転)成分** を分けて保持する。
両者を混ぜたまま扱うと「人手不足の解消」の議論が壊れるため。既定は `robotics_weight=0.35`
（LLMが主、物理自動化は一部で実装済み）で、`--scenario llm_only` / `llm_plus_robotics` で振れる。

---

## 企業レベルへの展開と P/L 換算

象限上の位置は業種で大部分が決まる。企業固有の差分は2つの属性だけで表現する。

- `labor_intensity`（労働集約度）→ 人手不足の「痛み」の大きさ（X軸）
- `knowledge_tilt`（知的労働比率）→ LLM が効く面積（Y軸）

いずれも業種平均からの乖離を low/mid/high で持ち、**正規化前の生値に対して** 適用する
（正規化後に足すと首位業種の銘柄が上限に張り付いて差が消えるため）。

財務データを渡すと、象限上の位置が営業利益への感応度に翻訳される:

```bash
uv run --no-sync python -m labor_ai_quadrant build \
    --financials path/to/financials.csv --out reports/quadrant.html
```

`financials` は `code, revenue, operating_profit, labor_cost, employees` を持つ
CSV / Parquet / JSON。

```
営業利益押上げ余地(%) = 人件費 × AI代替可能な労働の割合 × 実現率 ÷ 営業利益
```

実現率（既定 0.30）は「技術的に代替可能」と「実際に人件費が減る」のギャップ。

---

## ユニバース

既定は `reference/universe_jp.toml` のキュレーション済み **211銘柄**（東証33業種を網羅、
オフラインで完結）。上場全銘柄や TOPIX 500 を厳密に使う場合は J-Quants に切り替える:

```bash
export JQUANTS_MAIL_ADDRESS=... JQUANTS_PASSWORD=...
uv run --no-sync python -m labor_ai_quadrant build --universe jquants --scale topix500
uv run --no-sync python -m labor_ai_quadrant verify-universe   # キュレーション版の検証
```

`ScaleCategory` から TOPIX 500 = Core30 + Large70 + Mid400 を厳密に再現する。

---

## プロジェクト構成

```
labor_ai_quadrant/
├── src/labor_ai_quadrant/
│   ├── reference/           # キュレーション済み参照テーブル (TOML, 出典コメント付き)
│   │   ├── sector_labor_shortage.toml    # 33業種 × 人手不足6指標
│   │   ├── occupation_ai_exposure.toml   # 15職業 × LLM/物理ポテンシャル
│   │   ├── sector_occupation_mix.toml    # 33業種 × 15職業 構成比 + 規制ドラッグ
│   │   └── universe_jp.toml              # 銘柄ユニバース
│   ├── reference.py         # 読み込み + 検証（壊れたら大きな声で落ちる）
│   ├── axes.py              # 2軸のスコアリング
│   ├── quadrant.py          # 象限割り当て・脱出ポテンシャル
│   ├── company.py           # 企業展開 + P/L換算
│   ├── report.py            # オフラインHTMLレポート
│   ├── cli.py               # python -m labor_ai_quadrant
│   └── providers/jquants.py # 上場全銘柄取得（要ネットワーク、stdlibのみ）
├── tests/
└── docs/METHODOLOGY.md      # 定義・出典・限界（読むこと）
```

---

## 注意事項

- 両軸とも **33業種内の相対順位**（0-100）であり、絶対水準ではない。
  「右上に入る」＝「日本の上場企業の中で相対的に条件が良い」の意。
- 人手不足指標は公表統計に基づく **業種配賦値**、AI代替ポテンシャルは
  文献アンカー付きの **analyst 設定値**。個々のセルの精度ではなく、業種間の順序に意味がある。
- 銘柄コードと33業種は JPX の業種別分類に基づくが、再編・非上場化で変動する。
  実運用の前に `verify-universe` で検証すること。
- 投資判断そのものではない。人手不足という制約に対する感応度の地図であって、
  バリュエーションも競争優位も織り込んでいない。
- 前提と限界の詳細は [docs/METHODOLOGY.md](docs/METHODOLOGY.md)。
