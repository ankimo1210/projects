# §28.5 Extension to Several Factors — M30受入

更新2026-10-04。原典 Hull GE pp.679–680／脚注7を直接画像照合。基点main `7ac2f470`。MF01–06を全5軸へ対応。印刷数値pinはなく、以下の数値例は合成市場。

## 実装と独立検証

- private因子計算とprivate教材を追加。C=L Lᵀ、同じbasisのsigned loading／risk vector、比の相対Itô drift／log drift、可積分な有限GBMの条件付き平均、同じ給付のQ/g価格を扱う。PSD退化でinverseは不要。
- API46＋numerical4＋model index473＝523 tests PASS。混合boolの入力昇格をRED3→GREEN46で拒否。独立math.fsum／Gaussian求積11市場・132条件付き状態、262144標本・187 raw MC集計。最大API差1.4210854715202004e−14、最大MC差2.545394734466418 SE、8変異を拒否。
- lesson consumer16 tests。再署名した教師／保存結果も消費時に拒否。4共有図、新11セル／全268セルfresh実行、旧257セルの本文・保存出力・Plotly保持。価格図のsame-f契約はRED1→GREENで3種類のgを固定。
- Book／portal×1440／1000pxの16状態／16画像、数値・SE・表示変異・MathJax・図幅700px以上を確認。executorはportal1000全4図とBook1440全4図を目視。全198図、exotics86、public72／private33。Book warnings148＝従来144＋新Plotly4。

## 既受入29節と五軸台帳

初回はclean `6d7cf486` から29節を再描画。個別pytest計2215件、478画像のpayload合計20,387,859バイト、browser／runtime／C・F両保管庫の復元PASS。重複排除後の物理的な増加容量は未測定。

共有registryのimport整列後、HTMLは整列前と同じSHA-256。clean `abc68f37` から29節をD1 driverで再実行し、全29節を適格な既存画像から再利用した。個別pytest2215件／478画像／新規画像保存0バイト。採用パス・SHA・現行producer inventory・両保管庫は `m30-check.json` に固定した。証跡の手動再署名は行っていない。

統合gate、更新前拒否20 tests、全五軸台帳と `verify_section_ledger.py --check-artifacts` はPASS。作業ブランチ30受入／276未評価、P3 5/37（残32節）。

## 最終工程

初回全suite4219 passed・6 skipped、従来warnings2（279.33秒）、ruff19／tracked release PASS。最終source hash更新後の全suiteは4219 passed・6 skipped・従来warnings2（272.81秒）。4 --check／ruff19／tracked release／台帳成果物／29D1の現行hash・両保管庫がPASS。fresh最終レビュー／main FF・pushはpending。1名のfreshレビューを完了し、Important1を4回帰RED→lesson20GREENで修正。固定seed再生成の消費時完全照合を追加。修正後全suiteとmain FF／pushはpending。mainはまだM29までの29/277・P3 4/37。

## 範囲と制約

一般の局所martingaleを真のmartingaleと断定しない。一定GBM価格例をM29の確率金利教材の代替にしない。時刻0や決定論の場合に異なる観測値を置いた例は別の初期市場。丸め域を超えた非PSD、不正domain／型／非有限、表現不能なoverflow／正の条件付き平均underflowは拒否。全実数領域の浮動小数点精度を保証しない。

次はM31 §28.6。後続Ch29–34の原典調査／独立scratchは準備資料で、正式受入ではない。P3全37節の完了目標はactive。

## 最終レビュー

Critical0／Important1／Minor2。Importantの再署名MC消費ガードを修正し、全4回帰RED→lesson20GREEN。M1/M2は現在数値への影響なく保留。詳細は [レビュー](SECTION_28_5_REVIEW_2026-10-04.md)。全suite修正後再実行とmain統合は次工程。
