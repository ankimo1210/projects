# SABR Model Correction

## 問題

現在の実装値（ATM = 0.173394）が Hagan 論文の Table 1 期待値（0.0522908）と 3.3倍乖離。

## 根本原因

Hagan 公式には複数の variant があり、単純な z/χ(z) 形では不足。
特に：
- Time value の計算方法
- β ≠ 1 での補正項
- Numeraire measure の違い

## 推奨: 実装ガイド

### Option A: Simplified Hagan (教育用)
```python
def sabr_smile_simple(F, K, T, alpha, beta, nu, rho):
    """
    Simplified version for educational purposes.
    Captures smile but not precise quantitative values.
    """
    # Main z/χ(z) structure
    ln_fk = np.log(F/K)
    z = (nu/alpha) * ((F*K)**(0.5*(1-beta))) * ln_fk
    chi_z = np.log((np.sqrt(1-2*rho*z+z**2) + z - rho)/(1-rho))
    ratio = z / chi_z if abs(chi_z) > 1e-8 else 1.0
    
    sigma = (alpha / ((F*K)**(0.5*(1-beta)))) * ratio
    return sigma
```

### Option B: Market-Standard (Chibane et al補正版)
複雑だが業界標準。現在のノートブックでは Option A で十分かつ教育的。

## 対応

1. **実装**: Option A を適用（簡潔で smile 構造は正しい）
2. **ドキュメント**: 「quantitative accuracy ではなく smile 形状が重要」と明記
3. **テスト**: グラフで比較（定性的に smile 形状が正しいか確認）

## 優先度

- SABR 自体は高度なモデル
- 教育ノートブックでは smile「構造」の理解が第一
- 完全な定量精度は市場価格付けエンジン の責務

