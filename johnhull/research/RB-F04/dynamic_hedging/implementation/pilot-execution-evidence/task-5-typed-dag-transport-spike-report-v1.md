# Artifact-local typed DAG / unique arrays / compressed metadata: synthetic spike

**Outcome:** feasible for the tested normalized payload types. Every logical edge is independently expanded into writable dict/list/ndarray objects; identical values do not become shared mutable returned objects. Exact current reference payload_digest matches the original in all tests and all four measured fixtures. This is a throwaway feasibility prototype, not a production format or implementation approval.

The prototype interns typed metadata nodes and dtype/shape/actual-byte arrays only inside one artifact. A candidate hash is followed by typed-byte comparison on writes. It losslessly compresses the metadata table with zlib and saves unique arrays with compressed NPZ. Reads verify physical bindings, topological/reference coverage, all original occurrence counts and the existing full normalized logical digest, then create a fresh container or ndarray.copy at every edge. HestonParameters are reconstructed as separate instances.

Exact static AST extraction of run_reference's _digest/_encode_tree/_decode_tree/payload_digest and the parameter class avoids importing financial modules. Reference source bytes remained stable. No numerical pricing/Greek/finance qualification is inferred from these byte/digest checks.

## Small measurements

Single in-memory runs on the current host, including full logical digest costs. Write/read columns are **literal / prototype milliseconds**. Literal is a representative uncompressed tree+array-descriptor JSON and occurrence-per-array compressed NPZ, not the full production page/receipt format. Prototype physical totals also include a small root index. These measure the joint DAG+intern+compression effect, without ablation.

| Fixture | Original full array logical bytes | Literal physical bytes | Prototype physical bytes | Write ms | Read ms |
|---|---:|---:|---:|---:|---:|
| tiny_unique | 128 | 2,261 | 2,150 | 2.333 / 0.489 | 0.482 / 0.281 |
| repeated_metadata_128 | 16,384 | 282,296 | 2,172 | 13.328 / 28.872 | 11.959 / 7.651 |
| repeated_two_MiB | 2,097,152 | 511,480 | 7,951 | 63.494 / 16.474 | 10.049 / 5.688 |
| unique_arrays_two_MiB | 2,097,152 | 446,011 | 324,707 | 58.848 / 70.101 | 10.141 / 11.782 |

The repeated 2 MiB input retains all 64 array occurrences on decode while physically saving one unique array. The unique-array control retains all 64 unique arrays and shows a smaller saving. Metadata-heavy repeated input and the unique-array control have slower prototype encoding; compression is not a guaranteed speedup.

Returned payload logical bytes and full digest traversal remain. This does not estimate real 300+ MiB metadata, native NPZs, original wholephase capacity/runtime or ETA. No business NPZ or large JSON was read. Filesystem write/read, production pages/256 MiB pack splitting, bounded decompression/RSS, malformed-type security and full legacy/restore compatibility remain unverified. Object/structured arrays and non-string dictionary keys are outside this prototype's support; reserved marker input collisions in the existing literal codec are not redefined. Tuple-to-list and NumPy scalar normalization follow the existing reader.

## Verification and unchanged scope

Five meaningful synthetic tests PASS: original digest and complete occurrence counts; nested mask/covariance/fit/status/cost inplace isolation; scalar bool/int/float/nonfinite/signedzero; distinct Heston instances; array dtype/shape/NaN payload bits/empty/0d/endian/strided/Fortran logical values; and compressed-metadata tamper/cycle rejection. Root fields include original_N=1024, all 12 fits per row and 16 blocks, unknown qualification and original supplied costs. RED five failures remains preserved; final five tests and Ruff/format two files PASS.

Four fixture measurements completed in enclosing 0.441 s / CPU 1.752 s. Peak process RSS 50,163,712 B includes NumPy import and all fixture stages; it is not an incremental per-case RSS. No RNG/SDE/solver/worker, native/CAS/Git, production source edits, or real hardlink execution. Both existing hardlink helpers v1/v2 remain byte-identical. Design decisions and any production implementation are separate work.
