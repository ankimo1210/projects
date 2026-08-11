from __future__ import annotations

import numpy as np
import pytest
from quant_textbook.sec_features import (
    fit_hashed_tfidf,
    fit_numeric_preprocessor,
    fit_sparse_ridge,
    load_sec_teaching_fixture,
    regression_error_table,
)
from scipy import sparse


def test_bundled_fixture_is_development_only_and_integrity_checked() -> None:
    fixture = load_sec_teaching_fixture()

    assert fixture.numeric_features.shape == (256, 12)
    assert fixture.token_hashes.shape == (256, 128)
    assert fixture.training_mask.sum() == 192
    assert fixture.validation_mask.sum() == 64
    assert not np.any(fixture.target_available_dates >= np.datetime64("2023-10-23"))
    assert set(fixture.partitions) == {"inner_train", "inner_validation"}
    assert len(set(fixture.row_ids)) == 256
    assert all(len(value) == 64 for value in fixture.document_sha256)


def test_numeric_preprocessing_uses_only_selected_training_rows() -> None:
    features = np.array([[1.0, np.nan], [3.0, 2.0], [1000.0, 1000.0]])
    training = np.array([True, True, False])
    preprocessor = fit_numeric_preprocessor(features, training)
    transformed = preprocessor.transform(features)

    np.testing.assert_allclose(preprocessor.medians, [2.0, 2.0])
    np.testing.assert_allclose(preprocessor.means, [2.0, 2.0])
    assert transformed.shape == (3, 4)
    np.testing.assert_array_equal(transformed[:, 2:], np.isnan(features))


def test_tfidf_vocabulary_and_idf_are_training_only() -> None:
    tokens = np.array([[1, 1, 2], [1, 3, 3], [999, 999, 999]])
    training = np.array([True, True, False])
    model = fit_hashed_tfidf(tokens, training, maximum_features=5, minimum_document_frequency=1)
    transformed = model.transform(tokens)

    assert 999 not in model.vocabulary
    assert sparse.isspmatrix_csr(transformed)
    np.testing.assert_allclose(np.sqrt(transformed.multiply(transformed).sum(axis=1)).A1[:2], 1.0)
    assert transformed[2].nnz == 0


def test_sparse_ridge_recovers_a_low_noise_linear_signal() -> None:
    rng = np.random.default_rng(42)
    features = sparse.csr_matrix(rng.normal(size=(100, 4)))
    target = 0.5 + features.toarray() @ np.array([1.0, -2.0, 0.0, 0.5])

    model = fit_sparse_ridge(features, target, ridge=1e-8)

    np.testing.assert_allclose(model.predict(features), target, atol=1e-7)
    assert model.intercept == pytest.approx(0.5, abs=1e-7)


def test_regression_error_table_uses_equal_company_weighting() -> None:
    actual = np.array([0.0, 0.0, 0.0, 10.0])
    predicted = np.zeros(4)
    entities = np.array(["a", "a", "a", "b"])

    metrics = regression_error_table(actual, predicted, entities)

    assert metrics["mae"] == pytest.approx(2.5)
    assert metrics["company_macro_mae"] == pytest.approx(5.0)


@pytest.mark.parametrize("ridge", [-1.0, np.inf])
def test_sparse_ridge_rejects_invalid_penalties(ridge: float) -> None:
    with pytest.raises(ValueError, match="ridge"):
        fit_sparse_ridge(np.ones((3, 1)), np.ones(3), ridge=ridge)
