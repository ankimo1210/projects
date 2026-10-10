# Typed-DAG transport v2: bounded page-wrapper header

- v1 sources, manifest and independent counterexample are unchanged.
- Added _validate_blob_npy_header before protocol.read_artifact: parse a bounded ZIP_STORED blob.npy header, require uint8, one-dimensional tuple, fortran_order=False, declared bytes within the wrapper bound, and exact header+body length matching the ZIP member.
- The original self-consistent tiny NPZ declaring a 1 GiB array is rejected before reaching the array reader. The synthetic spy prevents the former allocation path; no large array is allocated.
- Extracted validate_empty_root_container(directory) from the original read_transport guard. read_transport calls it before protocol reading; root owns the same entry check in read_pilot_artifact.
- RED-v2-header.log preserves 7 original failures. GREEN-v2.log: 44 passed in 1.60 seconds (37 original + 7 boundary regressions). Ruff/format: both owned files PASS.
- Mathematics, N, logical payload, tuple/np.scalar normalization, occurrence isolation, legacy protocol, teacher recipe, production dependencies and W1 source were not changed.
- The candidate is source transport only; actual finance, capacity, RSS, large-workload speed and formal acceptance remain unknown. Root-owned integration and independent review are separate.
