# QuantLib 1.43 API導入資料（C/Dのみ）

承認環境で `import QuantLib as ql` が使える。配布した公式ヘッダと
Pythonの `help(ql.DiscountCurve)`、`help(ql.FlatForward)` 等を参照できる。
ネットワークアクセスや追加インストールは不要。

```python
import QuantLib as ql
reference = ql.Date(15, 1, 2026)
flat = ql.FlatForward(reference, -0.005, ql.Actual365Fixed(), ql.Continuous)
print(flat.discount(1.25))  # continuous year fraction, not a rounded Date
curve = ql.DiscountCurve(
    [reference, reference + 365, reference + 730],
    [1.0, 0.98, 0.955], ql.Actual365Fixed())
print(curve.discount(1.25))
```

合成ベンチマークの実数年限を暦日に丸めると別の契約になる。
ライブラリを使う箇所と、公開規約を忠実に実装する接続部分を分けて明示する。
QuantLibの利用自体を成功とせず、現行方式との精度・実行時間・保守性を検証する。
グローバルなvaluation dateを使うAPIでは設定・再現性を記録する。

Source: https://www.quantlib.org/
Source: https://github.com/lballabio/QuantLib/tree/v1.43/ql/termstructures/yield

QuantLibはBSD-3-Clause。配布ヘッダの著作権表示は保持する。
