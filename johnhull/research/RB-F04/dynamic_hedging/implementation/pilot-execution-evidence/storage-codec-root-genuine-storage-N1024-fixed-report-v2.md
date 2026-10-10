# Genuine original N1024 storage-only measurement

## Result

Same full closed nonteacher artifact market:pilot:Heston:1:N1024, seed57346572.
Original 1,024 paths, 1,648 logical arrays and all keys/status/cost/claim fields
were retained; no path reduction, solver, training or new random draw.

| Metric | Original legacy | New typed DAG |
|---|---:|---:|
| Physical bytes | 122,958,383 | 40,225,790 |
| JSON file bytes | 579,746 | 2,628 |
| Logical array occurrences | 1,648 | 1,648 |
| Unique stored arrays | not deduplicated | 509 |
| Data/metadata pages | 1 legacy pack | 2 pages |

Physical size fell by67.3% for this one artifact. The complete reconstructed
return still contains all logical array occurrences. Metadata NDJSON is inside
compressed pages, so JSON file bytes are not the full expanded metadata size.

## Actual expense and scope

- Enclosing wall3.064856560s / CPU3.020272s.
- Child wall3.037452270s / CPU2.989217065s / kernel peakRSS986,394,624B.
- Parent peakRSS20,234,240B; no sampled resource stop or observation error.
- Legacyread0.291745072s, newwrite1.007632776s, newread0.365851979s.
- These phase clocks are subsets of the enclosing clock; they are not added again.
- Final enclosing receipt serialization is explicitly outside its preceding clock.
- Source and original six physical input files were byte-authenticated before/after.

All full values passed the existing rtol2e-9/atol2e-10/equal_nan comparison and
the existing complete logical storage digest. All1,648 output array occurrences
are independently writable with disjoint byte ranges;392 mutable containers
are distinct. A repeated-content array pair was mutated in place, siblings and
original remained unchanged, then the probe byte was restored and full logical
provenance checked again.

## Preserved failure / approval boundary

v1 used child RLIMIT_AS4GiB and stopped before array decode when importing
libtorch_cuda.so. Its original traceback, prior and0.542s enclosing expense
remain unchanged. Root explicitly authorized v2: observed individualRSS4GiB
at0.1s intervals plus AS64GiB auxiliary fender; child120s/enclosing180s remained.

Old generation native56815c... remains the original financial origin. New
storage runtime/codec source bindings are separate. Financial qualification
remains unknown. This is one124MB market artifact; it does not establish whole
phase compressed capacity, restored performance, high-N memory, numerical
finance quality or an end-to-end ETA. It is not a legacy-write speed comparison.

No production source/helper/test changes, CAS or Git were performed.
