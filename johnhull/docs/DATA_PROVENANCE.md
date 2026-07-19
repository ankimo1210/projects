# A5–A8 Data Provenance and Licensing

## Release policy

vol 18–25 の committed reference artifact は、リポジトリ内の数式・数値モデルから固定seedで生成した
小型の **synthetic data** だけである。市場データ、取引所データ、顧客データ、checkpoint、生のMonte Carlo
pathは含めない。vol 18–25 のnotebook実行、book build、新規volume page、portalはnetwork accessを
必要としない。A1–A4で使うRequireJSもMITライセンスの固定版を`book/_static/`へ同梱した。
同梱版はRequireJS 2.3.4で、原文licenseとSHA-256は`release_manifest.json`に固定している。

既存vol 1–17の数式pageは、従来からJupyter Book既定のMathJax CDNを閲覧時に使う。このlegacy依存は
`release_manifest.json`で明示的にallowlistし、vol 18–25へ新しいremote runtime依存を持ち込まない。
したがって「全legacy pageを完全offlineで数式描画できる」という主張はしない。

各reference JSONは `data_policy: synthetic-offline`、generator名、schema version、対応NPZのSHA-256を持つ。
数値は教育・再現性検証用であり、収益性、市場予測力、production readinessの根拠にはしない。

## Optional market-data track

実市場で再検証する場合、利用者が契約・ライセンスを持つデータをignored directoryへ配置し、配布可能性を
データ提供者の条件に従って個別に確認する。Cboe、CME、ICE、取引所、vendor等のデータを本releaseから
再配布しない。optional trackの結果やcacheをcommitしない。

## Research maturity

未査読preprint由来のPDV/AFV、0DTE、signature、optimal transport、foundation model、diffusion等は
`research` trackとして扱う。core releaseは古典baseline、synthetic fixture、hard checkだけで再現でき、
research trackの失敗や未導入dependencyから独立する。

無効化されたtrackの正本は`johnhull/research_profiles.json`と、`deep_hedge_price/configs/research_*.yaml`である。
既定ではnetwork downloadもlocal checkpoint探索も行わない。
