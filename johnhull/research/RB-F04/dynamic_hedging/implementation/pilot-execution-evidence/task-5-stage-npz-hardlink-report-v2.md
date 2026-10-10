# D-only rollback failure fix (v2)

The immutable v1 helper (934f5337...) and all its 14 manifest entries remain unchanged. Existing 2124 real successful links are historical root evidence and are not changed or reclassified.

The new dedicated RuntimeError subclass propagates rollback replacement I/O failure past run's ordinary candidate-rejection catch. link retains the original staging backup, journals rollback_failed with effect unknown and both the initiating and rollback errors, and reports tool_exception. Even a failure while recording that event cannot erase the retained backup or downgrade the operation to rejected. The successful-link and normal administrative-cap rollback paths retain their existing behavior. Only link's existing AST changes, plus the dedicated exception declaration; run/limits/byte and receipt guards/detach/CLI/scope stay unchanged.

Regression: the same synthetic NPZ pair injects a post-replacement read cap and an OSError on original-backup replacement. Against immutable v1, the new assertion fails because no exception propagates (11 PASS / 1 FAIL). Against v2, original backup inode/bytes persist, target remains explicitly unknown/shared, receipt bytes remain unchanged, no released bytes or successful link are claimed, and rollback_failed/tool_exception propagate instead of rejected. Existing eleven tests are unchanged and pass.

Validation: 12 synthetic tests PASS (1.478 s unittest, enclosing 1.508 s / CPU 0.0926 s); Ruff and format 2 files PASS. Actual native reads/writes, financial/source/Git/CAS execution and production edits are zero. No real dedup invocation is authorized by this preparation. Fixed helper API/CLI is the same; root alone selects any subsequent real operation.
