# 不動産投資シミュレーター — ローカル Web アプリ

`real_estate_investment_sim_3.ipynb` の分析ロジックを Streamlit アプリ化したものです。
**ローカル専用** (127.0.0.1) で動作し、外部公開しません。

## ファイル構成

```
real_estate_app/
├── app.py                      # Streamlit メインアプリ
├── sim_engine.py               # 計算ロジック（v3 全関数）
├── charts.py                   # matplotlib チャート関数
├── config/
│   ├── default_params.json     # デフォルトパラメータ
│   └── saved/                  # ユーザー保存パラメータ
└── .streamlit/
    └── config.toml             # Streamlit ローカル設定

launch_streamlit_from_notebook.ipynb  # Notebook からの起動用
README_local_app.md                   # このファイル
```

## 必要パッケージ

- Python 3.10+
- streamlit
- pandas
- numpy
- matplotlib

## セットアップ

```bash
pip install streamlit pandas numpy matplotlib
```

日本語フォント（チャート用）:
```bash
# Ubuntu/WSL
sudo apt install fonts-ipaexfont
```

## 起動方法

### ターミナルから

```bash
cd ~/projects/notebooks/real_estate_app
python -m streamlit run app.py
```

ブラウザで http://127.0.0.1:8501 を開く。

### Jupyter Notebook から

`launch_streamlit_from_notebook.ipynb` を開き:

1. **セットアップセル** (初回のみ): pip install 実行
2. **起動セル**: Streamlit サーバーを起動
3. **停止セル**: サーバーを停止

### 起動セルコード（コピー用）

```python
import subprocess, sys, os, time

APP_DIR = os.path.expanduser("~/projects/notebooks/real_estate_app")

proc = subprocess.Popen(
    [sys.executable, "-m", "streamlit", "run", "app.py",
     "--server.address=127.0.0.1", "--server.port=8501",
     "--server.headless=true", "--browser.gatherUsageStats=false"],
    cwd=APP_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

time.sleep(2)
if proc.poll() is None:
    print(f"Streamlit 起動成功 (PID: {proc.pid})")
    print(f"URL: http://127.0.0.1:8501")
else:
    print("起動失敗")
    print(proc.stderr.read().decode())
```

### 停止セルコード（コピー用）

```python
proc.terminate()
proc.wait(timeout=5)
print("Streamlit 停止完了")
```

## アプリ機能

### サイドバー（パラメータ入力）
- 物件取得 / 収入 / 費用 / 借入 / インフレ・価格 / 税務 / CAPEX / 資本政策
- CAPEX・繰上返済スケジュールはインライン編集可能
- パラメータの保存・読込・デフォルト復元

### タブ
1. **Overview** — 主要指標カード + 投資概要テーブル
2. **Cash Flow** — 年次CF表 + 累積CF/Equity CFチャート
3. **PL** — Operating P/L 表 + チャート
4. **NAV / Economic P&L** — NAV表 + MV/Loan/NAVチャート
5. **Risk / Drawdown** — Drawdownメトリクス + 曲線チャート
6. **Scenarios** — マルチメトリクスシナリオ比較 + v3拡張シナリオ
7. **Ownership Compare** — 個人vs法人比較 + 3パネルチャート
8. **Tax / Exit Waterfall** — 売却税務/Tax Bridge/Exit Waterfall/資本政策イベント

## ローカル専用

- `.streamlit/config.toml` で `address = "127.0.0.1"` に固定
- `gatherUsageStats = false`
- 外部公開・クラウドデプロイは想定していません

## 将来の拡張候補

- [ ] Plotly インタラクティブチャート化
- [ ] PDF レポート自動生成
- [ ] 月次モデル対応
- [ ] Monte Carlo シミュレーション
- [ ] ポートフォリオ（複数物件）対応
- [ ] Docker コンテナ化
- [ ] 感応度ヒートマップ
