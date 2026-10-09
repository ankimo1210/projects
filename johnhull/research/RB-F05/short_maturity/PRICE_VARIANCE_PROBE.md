# RB-F05 conditioned price-label variance preflight

Independent deterministic centered second-moment integration; candidate conditions only. No main data or learning was generated.

Worst candidate: minutes=390, S=105.168670715, W=0.00015873015873, Lambda=0.028, C=5.274804437, Var(C|N,Zj)=1.172790242.

| N | Predicted SE(C) |
|---:|---:|
| 16384 | 0.008460581 |
| 65536 | 0.004230291 |
| 262144 | 0.002115145 |
| 1048576 | 0.001057573 |

Required N for population SE<=.002: 293198. Recommend adding 2^20 before pilot candidate freeze, without relaxing accuracy. Largest candidate SE at 2^18 exceeds .002; at 2^20 it passes with a margin. Pilot still must verify all slots, all streams and Delta/Gamma requirements.

Method: ordinary Poisson n=0..8; conditional Brownian CDF price integrated over jump normal z in [-14,14], centered on independent count-mixture expectation. Quadrature error and omitted Poisson centered-second-moment bound are saved separately. Gaussian-tail remainder is bounded using the tilted second moment; for this law cutoff14 gives a negligible (<1e-34 currency^2) remainder.

Time: 0.113 seconds for 42 deterministic integrations. {'262144': {'median_seconds_one_slot_counts_only': 0.0016476729651913047, 'max_slot_bytes_int64': 2097152, 'three_stream_84_slot_count_seconds_linear_estimate': 0.4152135872282088}, '1048576': {'median_seconds_one_slot_counts_only': 0.005707137985154986, 'max_slot_bytes_int64': 8388608, 'three_stream_84_slot_count_seconds_linear_estimate': 1.4381987722590566}}

Count timing is only a measured RNG component lower scope; it excludes conditional labels, compact aggregation, serialization and process overhead. Candidate maximum counts require 8MiB per slot at 2^20 versus 2MiB at 2^18. Materialize/serialize slot-wise; do not claim these component times as whole teacher cost. Population SE forecasts are not observed SE or coverage.
