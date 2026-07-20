from __future__ import annotations

import numpy as np
import pytest

from lob_reproductions.fixtures.queue_imbalance import QueueImbalanceFixture
from lob_reproductions.queue_imbalance.evaluation import (
    evaluate_binary_probability_forecast,
    null_model_metrics,
)
from lob_reproductions.queue_imbalance.local_logistic import (
    LocalLogisticRegression,
    cross_validate_bandwidth,
    tricube,
)
from lob_reproductions.queue_imbalance.logistic import ParametricLogisticRegression
from lob_reproductions.queue_imbalance.sampling import split_observations


def test_parametric_queue_signal_beats_null_and_reverses_with_feature_sign() -> None:
    observations = QueueImbalanceFixture(days=8, intervals_per_day=140).sample_paper_observations(
        observations_per_day=100
    )
    split = split_observations(observations, strategy="random", seed=7)
    train_x = observations.imbalance[split.train_index]
    train_y = observations.response[split.train_index]
    test_x = observations.imbalance[split.test_index]
    test_y = observations.response[split.test_index]

    model = ParametricLogisticRegression().fit(train_x, train_y)
    metrics = evaluate_binary_probability_forecast(test_y, model.predict_proba(test_x))
    null = null_model_metrics(test_y)
    assert model.converged_
    assert model.slope_ > 0
    assert metrics["roc_auc"] > 0.7
    assert metrics["mean_squared_residual"] < null["mean_squared_residual"]

    reversed_model = ParametricLogisticRegression().fit(-train_x, train_y)
    assert reversed_model.slope_ < 0
    np.testing.assert_allclose(
        model.predict_proba(test_x), reversed_model.predict_proba(-test_x), atol=1e-8
    )


def test_local_logistic_and_paper_bandwidth_cv_are_well_formed() -> None:
    observations = QueueImbalanceFixture(days=2, intervals_per_day=100).sample_paper_observations(
        observations_per_day=80
    )
    selected, scores = cross_validate_bandwidth(
        observations.imbalance,
        observations.response,
        candidates=(0.5, 0.65, 0.8),
        folds=3,
        seed=7,
    )
    assert selected in scores
    assert set(scores) == {0.5, 0.65, 0.8}
    assert all(np.isfinite(score) and score >= 0 for score in scores.values())
    model = LocalLogisticRegression(bandwidth=0.65).fit(
        observations.imbalance, observations.response
    )
    prediction = model.predict_proba(np.array([-0.5, 0.0, 0.5]))
    assert np.all((prediction >= 0) & (prediction <= 1))
    assert prediction[0] < prediction[-1]


def test_tricube_has_compact_support() -> None:
    weights = tricube(np.array([0.0, 0.5, 1.0, 1.5]), radius=1.0)
    assert weights[0] == 1.0
    assert 0 < weights[1] < 1
    assert weights[2] == 0.0
    assert weights[3] == 0.0


def test_local_logistic_stays_finite_and_monotone_under_perfect_separation() -> None:
    imbalance = np.array([-1.0, -0.8, -0.6, -0.4, 0.4, 0.6, 0.8, 1.0])
    response = np.array([0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0])
    model = LocalLogisticRegression(bandwidth=1.0).fit(imbalance, response)
    prediction = model.predict_proba(np.array([-0.9, 0.0, 0.9]))
    assert np.all(np.isfinite(prediction))
    assert np.all((prediction >= 0) & (prediction <= 1))
    assert prediction[0] < 0.5 < prediction[2]


def test_binary_forecast_evaluation_rejects_single_class_response() -> None:
    single_class = np.ones(6, dtype=np.int64)
    probability = np.full(6, 0.6)
    with pytest.raises(ValueError, match="single class"):
        evaluate_binary_probability_forecast(single_class, probability)
