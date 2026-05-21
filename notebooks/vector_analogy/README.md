# Vector Analogy Visualization

Small notebook and HTML generator for visualizing classic word embedding analogies such as:

```text
king - man + woman ~= queen
```

This example intentionally uses static word embeddings rather than a modern contextual LLM. The analogy is easier to explain with word2vec/GloVe-style vectors because every word has one fixed vector.

## Setup

From the workspace root:

```bash
python3 -m pip install gensim numpy plotly
```

The first run downloads the selected embedding model through `gensim.downloader`. The default model is `glove-wiki-gigaword-100`.
The output prints nearest-neighbor analogies, a dot-product / vector-norm / cosine-similarity comparison for `king - man + woman`, and pairwise similarity examples for related and distant words.

## Run

Generate an interactive HTML file:

```bash
python3 notebooks/vector_analogy/vector_analogy_visualization.py
```

Default output:

```text
notebooks/vector_analogy/vector_analogy.html
```

If `gensim` is unavailable or broken locally, generate a small offline demo with built-in toy vectors:

```bash
python3 notebooks/vector_analogy/vector_analogy_visualization.py --toy
```

Open the notebook for a step-by-step version:

```text
notebooks/vector_analogy/vector_analogy_visualization.ipynb
```

## Notes

- Most GloVe keys are lowercase, so use `king` rather than `King`.
- Dot product is useful, but it is affected by vector length. Cosine similarity is the normalized dot product and is usually better for comparing semantic direction.
- Pairwise examples include similar relations such as `king`/`queen`, inflections such as `walk`/`walking`, opposites such as `good`/`bad`, and distant concepts such as `king`/`tokyo`.
- `man - woman` is not a pure gender vector. It reflects usage patterns and biases in the training corpus.
- Transformer LLMs also have token embeddings, but their deeper representations are context dependent. This demo focuses on the classic static embedding result.
- `--toy` is only for checking the visualization mechanics. Use the default GloVe path for real pretrained vectors.
