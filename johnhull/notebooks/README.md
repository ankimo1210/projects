# notebooks/ — Ch.15 BSM (legacy location)

`bsm_chapter15.ipynb` **is the source of truth**. It is committed with its
executed outputs and deterministic cell ids, and it carries the teaching
scaffolds added after the last generator run.

There is no build script that regenerates it. The two whole-notebook
generators that used to live here (`build_bsm_notebook.py`,
`build_bsm_nb.py`) were deleted: they wrote to a stale absolute path outside
this repository and predated the scaffold pass, so running either one silently
discarded the committed outputs and the teaching content. Recover them from
git history (`git log -- johnhull/notebooks/`) only if you need the original
cell text.

To change the notebook, edit the `.ipynb` directly (or patch it in place, as
`patch_bsm_nb.py` does) and re-execute:

```bash
uv run --no-sync jupyter nbconvert --to notebook --execute --inplace \
    johnhull/notebooks/bsm_chapter15.ipynb
```

The same applies to `interest_rate_models/ir_models.ipynb`, whose builder
(`build_ir_models_notebook.py`) does write inside the repository and is still
usable.
