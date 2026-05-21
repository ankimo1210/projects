from __future__ import annotations

import argparse
import importlib.util
import math
from collections.abc import Iterable
from pathlib import Path

DEFAULT_MODEL = "glove-wiki-gigaword-100"
DEFAULT_OUTPUT = Path(__file__).with_name("vector_analogy.html")

ANALOGIES = [
    ("king", "man", "woman", "queen"),
    ("prince", "man", "woman", "princess"),
    ("paris", "france", "japan", "tokyo"),
    ("walking", "walk", "swim", "swimming"),
    ("better", "good", "bad", "worse"),
]

SIMILARITY_PAIRS = [
    ("king", "queen", "royalty gender pair"),
    ("prince", "princess", "royalty gender pair"),
    ("man", "woman", "gender contrast"),
    ("boy", "girl", "gender contrast"),
    ("father", "mother", "family gender pair"),
    ("uncle", "aunt", "family gender pair"),
    ("paris", "tokyo", "capital cities"),
    ("paris", "france", "capital-country relation"),
    ("tokyo", "japan", "capital-country relation"),
    ("london", "england", "capital-country relation"),
    ("berlin", "germany", "capital-country relation"),
    ("walk", "walking", "verb inflection"),
    ("swim", "swimming", "verb inflection"),
    ("run", "running", "verb inflection"),
    ("good", "better", "comparative"),
    ("bad", "worse", "comparative"),
    ("good", "bad", "opposite sentiment"),
    ("king", "tokyo", "distant concepts"),
    ("queen", "swimming", "distant concepts"),
]

CONTEXT_WORDS = [
    "king",
    "queen",
    "man",
    "woman",
    "prince",
    "princess",
    "boy",
    "girl",
    "father",
    "mother",
    "uncle",
    "aunt",
    "paris",
    "france",
    "japan",
    "tokyo",
    "london",
    "england",
    "berlin",
    "germany",
    "walking",
    "walk",
    "swim",
    "swimming",
    "run",
    "running",
    "better",
    "good",
    "bad",
    "worse",
]


class ToyStaticVectors:
    """Tiny deterministic embedding space for offline visualization checks."""

    def __init__(self) -> None:
        self.vectors = {
            "man": [0, 1, 0, 0, 0, 0, 0, 0],
            "woman": [0, 0, 1, 0, 0, 0, 0, 0],
            "king": [1, 1, 0, 0, 0, 0, 0, 0],
            "queen": [1, 0, 1, 0, 0, 0, 0, 0],
            "prince": [0.8, 1, 0, 0, 0, 0, 0, 0],
            "princess": [0.8, 0, 1, 0, 0, 0, 0, 0],
            "boy": [0, 0.8, 0, 0, 0, 0, 0, 0],
            "girl": [0, 0, 0.8, 0, 0, 0, 0, 0],
            "father": [0.2, 1, 0, 0, 0, 0, 0, 0],
            "mother": [0.2, 0, 1, 0, 0, 0, 0, 0],
            "uncle": [0.1, 1, 0, 0, 0, 0, 0, 0],
            "aunt": [0.1, 0, 1, 0, 0, 0, 0, 0],
            "france": [0, 0, 0, 0, 1, 0, 0, 0],
            "paris": [0, 0, 0, 1, 1, 0, 0, 0],
            "japan": [0, 0, 0, 0, 0, 1, 0, 0],
            "tokyo": [0, 0, 0, 1, 0, 1, 0, 0],
            "england": [0, 0, 0, 0, 0, 0, 1, 0],
            "london": [0, 0, 0, 1, 0, 0, 1, 0],
            "germany": [0, 0, 0, 0, 0, 0, 0, 1],
            "berlin": [0, 0, 0, 1, 0, 0, 0, 1],
            "walk": [0, 0, 0, 0, 0, 0, 0, 2],
            "walking": [0, 0, 0, 0, 0, 0, 1, 2],
            "swim": [0, 0, 0, 0, 0, 0, 0, 2.4],
            "swimming": [0, 0, 0, 0, 0, 0, 1, 2.4],
            "run": [0, 0, 0, 0, 0, 0, 0, 2.8],
            "running": [0, 0, 0, 0, 0, 0, 1, 2.8],
            "good": [0, 0, 0, 0, 1, 0, 0, 2],
            "better": [0, 0, 0, 0, 1, 0, 1, 2],
            "bad": [0, 0, 0, 0, -1, 0, 0, 2],
            "worse": [0, 0, 0, 0, -1, 0, 1, 2],
        }

    def __contains__(self, word: str) -> bool:
        return word in self.vectors

    def __getitem__(self, word: str) -> list[float]:
        return self.vectors[word]

    def __len__(self) -> int:
        return len(self.vectors)

    def most_similar(self, positive: list[str], negative: list[str], topn: int = 10):
        query = [0.0] * len(next(iter(self.vectors.values())))
        for word in positive:
            query = [left + right for left, right in zip(query, self.vectors[word], strict=False)]
        for word in negative:
            query = [left - right for left, right in zip(query, self.vectors[word], strict=False)]

        excluded = set(positive) | set(negative)
        scored = [
            (word, cosine_similarity(query, vector))
            for word, vector in self.vectors.items()
            if word not in excluded
        ]
        return sorted(scored, key=lambda item: item[1], reverse=True)[:topn]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = dot_product(left, right)
    left_norm = vector_norm(left)
    right_norm = vector_norm(right)
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def dot_product(left: Iterable[float], right: Iterable[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))


def vector_norm(vector: Iterable[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def ensure_dependencies(require_gensim: bool = True) -> None:
    modules = {
        "numpy": "numpy",
        "plotly": "plotly",
    }
    if require_gensim:
        modules["gensim"] = "gensim"
    missing = [
        package for package, module in modules.items() if importlib.util.find_spec(module) is None
    ]
    if missing:
        joined = " ".join(missing)
        raise SystemExit(
            f"Missing dependencies. Install them with:\n\npython3 -m pip install {joined}\n"
        )


def load_vectors(model_name: str):
    try:
        import gensim.downloader as api
    except Exception as exc:
        raise RuntimeError(
            "Could not import gensim. The installed package may be binary-incompatible "
            "with the current NumPy/SciPy stack. Try a clean environment, for example:\n\n"
            "python3 -m venv .venv\n"
            "source .venv/bin/activate\n"
            "python -m pip install gensim numpy plotly\n"
        ) from exc

    return api.load(model_name)


def analogy(vector_model, positive: Iterable[str], negative: Iterable[str], topn: int = 10):
    return vector_model.most_similar(positive=list(positive), negative=list(negative), topn=topn)


def vector_arithmetic(
    vector_model, positive: Iterable[str], negative: Iterable[str]
) -> list[float]:
    positive_words = list(positive)
    negative_words = list(negative)
    first_word = (positive_words + negative_words)[0]
    query = [0.0] * len(vector_model[first_word])
    for word in positive_words:
        query = [left + right for left, right in zip(query, vector_model[word], strict=False)]
    for word in negative_words:
        query = [left - right for left, right in zip(query, vector_model[word], strict=False)]
    return query


def available_words(vector_model, words: Iterable[str]) -> list[str]:
    return [word for word in dict.fromkeys(words) if word in vector_model]


def similarity_scores(
    vector_model,
    query: list[float],
    candidates: Iterable[str],
    topn: int = 10,
) -> list[dict[str, float | str]]:
    rows = []
    query_norm = vector_norm(query)
    for word in candidates:
        vector = vector_model[word]
        dot = dot_product(query, vector)
        norm = vector_norm(vector)
        cosine = 0.0 if query_norm == 0 or norm == 0 else dot / (query_norm * norm)
        rows.append(
            {
                "word": word,
                "dot_product": dot,
                "vector_norm": norm,
                "cosine_similarity": cosine,
            }
        )
    return sorted(rows, key=lambda row: row["cosine_similarity"], reverse=True)[:topn]


def analogy_similarity_scores(
    vector_model,
    a: str,
    b: str,
    c: str,
    topn: int = 10,
) -> list[dict[str, float | str]]:
    query = vector_arithmetic(vector_model, positive=[a, c], negative=[b])
    candidates = [
        word for word in available_words(vector_model, CONTEXT_WORDS) if word not in {a, b, c}
    ]
    return similarity_scores(vector_model, query, candidates, topn=topn)


def pair_similarity_scores(
    vector_model,
    pairs: Iterable[tuple[str, str, str]],
) -> list[dict[str, float | str]]:
    rows = []
    for left_word, right_word, label in pairs:
        if left_word not in vector_model or right_word not in vector_model:
            continue
        left = vector_model[left_word]
        right = vector_model[right_word]
        dot = dot_product(left, right)
        left_norm = vector_norm(left)
        right_norm = vector_norm(right)
        cosine = 0.0 if left_norm == 0 or right_norm == 0 else dot / (left_norm * right_norm)
        rows.append(
            {
                "left": left_word,
                "right": right_word,
                "label": label,
                "dot_product": dot,
                "left_norm": left_norm,
                "right_norm": right_norm,
                "cosine_similarity": cosine,
            }
        )
    return sorted(rows, key=lambda row: row["cosine_similarity"], reverse=True)


def build_projection(vector_model, words: list[str]):
    import numpy as np

    matrix = np.array([vector_model[word] for word in words], dtype=float)
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    points = centered @ vt[:2].T
    return {
        word: {"x": float(point[0]), "y": float(point[1])}
        for word, point in zip(words, points, strict=False)
    }


def create_figure(
    points: dict[str, dict[str, float]],
    analogy_rows: list[tuple[str, str, str, str]],
    similarity_rows: list[dict[str, float | str]] | None = None,
    pair_rows: list[dict[str, float | str]] | None = None,
):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    words = list(points)
    if similarity_rows or pair_rows:
        row_count = 1 + bool(similarity_rows) + bool(pair_rows)
        specs = [[{"type": "xy"}]]
        row_heights = [0.56]
        subplot_titles = ["PCA projection of selected word vectors"]
        if similarity_rows:
            specs.append([{"type": "table"}])
            row_heights.append(0.22)
            subplot_titles.append("Similarity to query: king - man + woman")
        if pair_rows:
            specs.append([{"type": "table"}])
            row_heights.append(0.22)
            subplot_titles.append("Pairwise similarity examples")
        fig = make_subplots(
            rows=row_count,
            cols=1,
            specs=specs,
            row_heights=row_heights,
            vertical_spacing=0.12,
            subplot_titles=tuple(subplot_titles),
        )
        scatter_row = 1
    else:
        fig = go.Figure()
        scatter_row = None

    scatter = go.Scatter(
        x=[points[word]["x"] for word in words],
        y=[points[word]["y"] for word in words],
        mode="markers+text",
        text=words,
        textposition="top center",
        marker={"size": 10, "color": "#2563eb"},
        hovertemplate="<b>%{text}</b><br>x=%{x:.3f}<br>y=%{y:.3f}<extra></extra>",
    )
    if scatter_row:
        fig.add_trace(scatter, row=1, col=1)
    else:
        fig.add_trace(scatter)

    table_row = 2
    if similarity_rows:
        fig.add_trace(
            go.Table(
                header={
                    "values": ["Rank", "Word", "Dot product", "Vector norm", "Cosine similarity"],
                    "fill_color": "#e5e7eb",
                    "align": "left",
                },
                cells={
                    "values": [
                        list(range(1, len(similarity_rows) + 1)),
                        [row["word"] for row in similarity_rows],
                        [f"{row['dot_product']:.4f}" for row in similarity_rows],
                        [f"{row['vector_norm']:.4f}" for row in similarity_rows],
                        [f"{row['cosine_similarity']:.4f}" for row in similarity_rows],
                    ],
                    "fill_color": "#ffffff",
                    "align": "left",
                },
            ),
            row=table_row,
            col=1,
        )
        table_row += 1

    if pair_rows:
        fig.add_trace(
            go.Table(
                header={
                    "values": [
                        "Rank",
                        "Word A",
                        "Word B",
                        "Example type",
                        "Dot product",
                        "Norm A",
                        "Norm B",
                        "Cosine similarity",
                    ],
                    "fill_color": "#e5e7eb",
                    "align": "left",
                },
                cells={
                    "values": [
                        list(range(1, len(pair_rows) + 1)),
                        [row["left"] for row in pair_rows],
                        [row["right"] for row in pair_rows],
                        [row["label"] for row in pair_rows],
                        [f"{row['dot_product']:.4f}" for row in pair_rows],
                        [f"{row['left_norm']:.4f}" for row in pair_rows],
                        [f"{row['right_norm']:.4f}" for row in pair_rows],
                        [f"{row['cosine_similarity']:.4f}" for row in pair_rows],
                    ],
                    "fill_color": "#ffffff",
                    "align": "left",
                },
            ),
            row=table_row,
            col=1,
        )

    arrow_pairs = []
    for a, b, c, expected in analogy_rows:
        if a in points and b in points:
            arrow_pairs.append((b, a, "base relation"))
        if c in points and expected in points:
            arrow_pairs.append((c, expected, "shifted relation"))

    annotations = []
    for start, end, label in arrow_pairs:
        annotations.append(
            {
                "x": points[end]["x"],
                "y": points[end]["y"],
                "ax": points[start]["x"],
                "ay": points[start]["y"],
                "xref": "x",
                "yref": "y",
                "axref": "x",
                "ayref": "y",
                "showarrow": True,
                "arrowhead": 3,
                "arrowsize": 1,
                "arrowwidth": 2,
                "arrowcolor": "#dc2626" if label == "base relation" else "#059669",
                "text": "",
            }
        )

    fig.update_layout(
        title="Word Embedding Analogies and Similarity Scores",
        template="plotly_white",
        width=1000,
        height=1120 if pair_rows else 900 if similarity_rows else 720,
        annotations=annotations,
        margin={"l": 40, "r": 40, "t": 80, "b": 40},
    )
    if similarity_rows or pair_rows:
        fig.update_xaxes(title_text="PCA 1", row=1, col=1)
        fig.update_yaxes(title_text="PCA 2", row=1, col=1)
    else:
        fig.update_xaxes(title_text="PCA 1")
        fig.update_yaxes(title_text="PCA 2")
    return fig


def print_analogy_table(vector_model, rows: list[tuple[str, str, str, str]], topn: int) -> None:
    for a, b, c, expected in rows:
        missing = [word for word in (a, b, c, expected) if word not in vector_model]
        if missing:
            print(f"\n{a} - {b} + {c} ~= {expected}")
            print(f"  skipped; missing from model: {', '.join(missing)}")
            continue

        results = analogy(vector_model, positive=[a, c], negative=[b], topn=topn)
        print(f"\n{a} - {b} + {c} ~= {expected}")
        for rank, (word, score) in enumerate(results, start=1):
            marker = " <==" if word == expected else ""
            print(f"  {rank:>2}. {word:<16} {score:.4f}{marker}")


def print_similarity_comparison(vector_model, a: str, b: str, c: str, topn: int) -> None:
    missing = [word for word in (a, b, c) if word not in vector_model]
    if missing:
        print(f"\nSimilarity comparison skipped; missing from model: {', '.join(missing)}")
        return

    rows = analogy_similarity_scores(vector_model, a, b, c, topn=topn)
    print(f"\nSimilarity comparison for query: {a} - {b} + {c}")
    print("  rank  word              dot_product  vector_norm  cosine_similarity")
    for rank, row in enumerate(rows, start=1):
        print(
            f"  {rank:>4}  {row['word']:<16}"
            f" {row['dot_product']:>11.4f}"
            f" {row['vector_norm']:>12.4f}"
            f" {row['cosine_similarity']:>18.4f}"
        )


def print_pair_similarity_table(
    vector_model, pairs: Iterable[tuple[str, str, str]], topn: int | None = None
) -> None:
    rows = pair_similarity_scores(vector_model, pairs)
    if topn is not None:
        rows = rows[:topn]
    print("\nPairwise similarity examples")
    print(
        "  rank  word_a        word_b        type                      dot_product  norm_a  norm_b  cosine"
    )
    for rank, row in enumerate(rows, start=1):
        print(
            f"  {rank:>4}  {row['left']:<12} {row['right']:<12}"
            f" {row['label']:<24}"
            f" {row['dot_product']:>11.4f}"
            f" {row['left_norm']:>7.4f}"
            f" {row['right_norm']:>7.4f}"
            f" {row['cosine_similarity']:>8.4f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize static word embedding analogies.")
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Gensim model name. Default: {DEFAULT_MODEL}"
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="HTML output path.")
    parser.add_argument("--topn", type=int, default=10, help="Number of nearest words to print.")
    parser.add_argument(
        "--toy",
        action="store_true",
        help="Use a tiny built-in embedding space; no gensim download.",
    )
    args = parser.parse_args()

    ensure_dependencies(require_gensim=not args.toy)
    try:
        model = ToyStaticVectors() if args.toy else load_vectors(args.model)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    print_analogy_table(model, ANALOGIES, args.topn)
    print_similarity_comparison(model, "king", "man", "woman", args.topn)
    print_pair_similarity_table(model, SIMILARITY_PAIRS)

    words = available_words(model, CONTEXT_WORDS)
    points = build_projection(model, words)
    similarity_rows = analogy_similarity_scores(model, "king", "man", "woman", topn=args.topn)
    pair_rows = pair_similarity_scores(model, SIMILARITY_PAIRS)
    fig = create_figure(points, ANALOGIES, similarity_rows=similarity_rows, pair_rows=pair_rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(args.output, include_plotlyjs="cdn")
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
