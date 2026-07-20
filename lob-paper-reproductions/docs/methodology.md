# Methodology

1. PDF/official codeを version/commit と SHA-256 で固定する。
2. material field を profile YAML と provenance locator に対応付ける。
3. 合成 fixture で shape、axis、label alignment、boundary、leakage を先に検証する。
4. author profile は logits/gradient/one-step/EMA の比較可能な seam を保つ。
5. real data result は dataset variant、split、label、horizon、feature、metric が一致する
   場合だけ比較する。

Synthetic results の report header は `STRUCTURAL REPRODUCTION ON SYNTHETIC DATA` とし、
論文の numerical replication とは表現しない。

