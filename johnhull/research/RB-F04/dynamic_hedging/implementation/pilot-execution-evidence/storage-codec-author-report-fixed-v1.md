# Nonteacher typed-DAG transport candidate

- Fixed implementation scope: _pilot_transport.py and its self-contained synthetic tests only.
- API: write_transport(..., protocol, runner, page_raw_limit=64*1024**2) and read_transport(..., root_metadata, root_receipt, protocol, runner).
- Schema rb-f04-pilot-typed-dag-v1. Array pages stream complete canonical C-order NPY headers and bodies; metadata pages stream typed NDJSON node/array records. Root is exposed only after all pages and its receipt close successfully.
- Each raw expanded page is at most the declared limit (maximum 64 MiB). ZIP_STORED single-member NPY preflight bounds compressed-blob allocation before the existing protocol reader; zlib output is bounded before expansion and must end exactly without trailing bytes.
- All root/page receipts, ordered ranges, node/array reachability, complete byte coverage, NPY header/body lengths and existing full logical payload digest are checked. Digest/SHA checks are storage provenance.
- Each decoded occurrence has independently writable containers/arrays; structured padding bytes and NaN payload bits are retained. Unique-array cache is bounded by the page limit; a larger returned array is not retained in a hidden second cache.
- RED: 23 failures caused by absent helper (RED-v2.log). Earlier collection/PYTHONPATH failure is preserved separately (RED-v1.log).
- GREEN: 37 dedicated synthetic checks passed in 1.59 seconds; Ruff and format checks passed for both files.
- No financial generation, real native reads, CAS, Git, production dependencies or mathematical changes were performed.
- Root-owned dispatch/source closure and legacy-reader integration are separate verification. Teacher recipe is not implemented or modified here.
- Limits: a single metadata record, the complete DAG table and the fully expanded logical return remain distinct RAM costs. This candidate does not guarantee workload RSS, speed, capacity, restore acceptance or financial qualification. Whole logical payload digest still traverses all occurrences.
