from __future__ import annotations

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

from lob_reproductions.fixtures.universal import UniversalMultiAssetEventFixture
from lob_reproductions.universal_features.paper_constrained import PaperConstrainedUniversalLSTM
from lob_reproductions.universal_features.protocols import (
    run_synthetic_linear_comparison,
    run_synthetic_lstm_comparison,
)


def test_histories_preserve_asset_day_boundaries_and_unseen_metadata() -> None:
    fixture = UniversalMultiAssetEventFixture(events_per_asset=400, events_per_day=200)
    histories = fixture.histories(history=100, stride=25)
    assert histories.features.shape[1:] == (100, 8)
    starts = histories.endpoint_index - 99
    assert np.all(starts // 200 == histories.endpoint_index // 200)
    assert np.all(histories.unseen_asset == (histories.asset_id >= fixture.training_assets))
    assert set(histories.asset_id[histories.unseen_asset]) == set(fixture.unseen_asset_ids)


def test_universal_mapping_improves_unseen_asset_protocol_and_shuffling_breaks_it() -> None:
    universal_fixture = UniversalMultiAssetEventFixture(
        events_per_asset=400, universal_mapping=True
    )
    nonuniversal_fixture = UniversalMultiAssetEventFixture(
        events_per_asset=400, universal_mapping=False
    )
    universal_result = run_synthetic_linear_comparison(universal_fixture)
    nonuniversal_result = run_synthetic_linear_comparison(nonuniversal_fixture)
    universal_accuracy = universal_result["universal_pooled_linear_unseen_accuracy"]
    nonuniversal_accuracy = nonuniversal_result["universal_pooled_linear_unseen_accuracy"]
    assert universal_accuracy > 0.85
    assert universal_accuracy - nonuniversal_accuracy > 0.08

    train_x = universal_fixture.features[universal_fixture.training_asset_ids].reshape(-1, 8)
    train_y = universal_fixture.labels[universal_fixture.training_asset_ids].reshape(-1)
    unseen_x = universal_fixture.features[universal_fixture.unseen_asset_ids].reshape(-1, 8)
    unseen_y = universal_fixture.labels[universal_fixture.unseen_asset_ids].reshape(-1)
    shuffled = np.random.default_rng(7).permutation(train_y)
    shuffled_model = LogisticRegression(C=1e6, max_iter=500, random_state=7).fit(train_x, shuffled)
    shuffled_accuracy = accuracy_score(unseen_y, shuffled_model.predict(unseen_x))
    assert abs(shuffled_accuracy - 0.5) < 0.1
    assert universal_accuracy - shuffled_accuracy > 0.25


def test_paper_constrained_lstm_shapes_state_detach_and_small_batch_overfit() -> None:
    model = PaperConstrainedUniversalLSTM(input_features=4, hidden_units=12)
    features = torch.randn(8, 10, 4)
    targets = torch.tensor([0, 1, 0, 1, 0, 1, 0, 1])
    logits, trace = model.shape_trace(features)
    assert logits.shape == (8, 2)
    assert trace[1]["shape"] == [3, 8, 12]
    _, state = model(features)
    detached = model.detach_state(state)
    assert detached[0].grad_fn is None and detached[1].grad_fn is None

    optimizer = torch.optim.Adam(model.parameters(), lr=0.03)
    for _ in range(100):
        optimizer.zero_grad(set_to_none=True)
        logits, _ = model(features)
        loss = torch.nn.functional.cross_entropy(logits, targets)
        loss.backward()
        optimizer.step()
    with torch.no_grad():
        final_logits, _ = model(features)
        final_loss = torch.nn.functional.cross_entropy(final_logits, targets)
    assert final_loss.item() < 0.15
    assert torch.equal(final_logits.argmax(dim=1), targets)


def test_scaled_lstm_protocol_covers_asset_specific_pooled_and_unseen_paths() -> None:
    fixture = UniversalMultiAssetEventFixture(events_per_asset=400, events_per_day=200)
    result = run_synthetic_lstm_comparison(fixture, epochs=3, hidden_units=6)
    assert set(result["asset_specific_lstm_accuracy"]) == {"0", "1", "2", "3"}
    assert 0 <= result["universal_pooled_lstm_unseen_accuracy"] <= 1
    assert np.isfinite(result["universal_pooled_final_training_loss"])
    assert result["claim_limit"] == "scaled synthetic LSTM protocol test only"
