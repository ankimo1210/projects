# Stage leaf NPZ hardlink preparation

- Preparation only: actual native reads/writes, CAS, financial/solver/RNG/SDE execution, production/Git edits: **0**.
- Fixed CLI root: task-5-formal-pilot-root-v2. Only direct jobs/stage:*/pack*/arrays.npz with exactly metadata.json/arrays.npz/receipt.json qualify. Root arrays and all teacher jobs are excluded. The leaf receipt establishes a closed writer; this does not assert the whole job is closed.
- Standard array receipt canonical bytes/artifact SHA, metadata byte SHA, actual stream NPZ SHA and size, ZIP-directory expanded size are authenticated. No array values are decoded. Both source/target are streamed again before mutation and after replacement. Symlink components and owner/group/mode/filesystem differences are rejected; inode/size/mtime are checked before/after.
- Staging is outside native, fixed under D on the same filesystem. Intent JSONL is flushed and fsynced before mutation. A staging link to the original target permits rollback on a post-link administrative cap or failed postcheck. The replacement changes only the duplicate arrays.npz directory entry; receipt and metadata bytes remain unchanged. Canonical inode/mtime is preserved, replacement inode/mtime intentionally becomes the canonical one.
- Certain released allocated bytes count only original targets whose immediate pre-replace nlink is 1 and whose rollback link is the final remaining old-inode link at removal. Selected inode-unique allocated before/after and native filesystem free values are separate fields. Windows host/VHD free-space reclamation is neither measured nor guaranteed.
- Administrative max read/link/time stops are explicitly partial and never financial caps or qualification. Application file reads include stream hashing and ZIP-directory reads; kernel readahead is not predicted. Final finished-journal emission is additional enclosing root cost. The tool never edits original financial cost/history files.
- Detach reads the successful linked records from the chosen original journal, verifies current bytes/receipt/source, streams a new copy into D staging, then atomically replaces the duplicate path. Byte/receipt values are preserved and inode sharing is removed. Interrupted intentions without a successful linked record are not automatically treated as completed operations.

## Validation

Meaningful synthetic tests: **11 PASS** (0.334 s unittest / enclosing 0.367 s); Ruff and format checks: **2 files PASS**. Covered exact duplicates with distinct receipts, self-consistent unequal bytes, forged receipt equality, incomplete packs/root and teacher exclusions, already linked skip, detach, external old hardlinks/zero overclaim, symlinks and mode mismatch, read cap, dry plan, one-link cap, and postcheck read-cap rollback preserving the original inode. RED 9 failures and the intermediate JSONL escape defect (7 passed/2 errors) remain recorded.

## Root use

The module's internal engine supports a selected pair without scanning the corpus:

    engine = Deduplicator(root=module.NATIVE_ROOT, staging=module.STAGING,
                          journal=new_direct_D_file, max_read_bytes=10737418240,
                          max_links=1, max_seconds=180)
    engine.prepare()
    source = engine.load_pack(fixed_source_arrays_path)
    target = engine.load_pack(fixed_target_arrays_path)
    engine.link(source, target)
    engine.finish((source, target))

Use finally to close/record finish if the root wrapper raises. Manual load_pack does not increment run's eligible roster counter; record the selected-pair count in the root enclosing receipt. This preparation grants no real execution approval.

Bounded CLI example (root selects and authorizes actual limits and new journal):

    python task-5-stage-npz-hardlink-v1.py --mode link --journal /absolute/D/new-root-journal.jsonl --max-read-bytes 10737418240 --max-links 1 --max-seconds 180

Read-only mode is --mode plan. Successful journal-owned links can be detached with --mode detach --detach-journal /absolute/D/original-root-journal.jsonl and a different new --journal. CLI has no arbitrary native-root override. Limit termination exits 2 with the completed/partial mutations explicit in the journal; it is unrelated to the formal pilot status.
