"""Check the actual digit task, especially leakage and portable weight layout."""

import base64

import numpy as np
import torch
from nn_textbook.digit_experiment import DigitCNN, pack_weights, prepare_data, train_model


def test_digit_split_uses_only_official_train_and_fixed_intensity_scaling():
    images = torch.arange(40 * 784).reshape(40, 28, 28).remainder(256).byte()
    labels = torch.arange(40).remainder(10)
    test_images = torch.full((10, 28, 28), 255, dtype=torch.uint8)
    split = prepare_data(images, labels, test_images, torch.arange(10), validation_size=10)
    assert len(split["train"]["ids"]) == 30
    assert set(split["train"]["ids"]).isdisjoint(split["validation"]["ids"])
    assert set(split["train"]["ids"]) | set(split["validation"]["ids"]) == set(range(40))
    assert torch.equal(split["test"]["x"], torch.ones(10, 1, 28, 28))
    assert torch.equal(torch.bincount(split["validation"]["y"]), torch.ones(10).long())


def test_digit_portable_weights_match_pytorch_layout_and_parameter_counts():
    for channels, expected in [([4, 8], 2410), ([12, 24], 8938)]:
        model = DigitCNN(channels)
        assert sum(p.numel() for p in model.parameters()) == expected
        assert model(torch.zeros(2, 1, 28, 28)).shape == (2, 10)
        packed = pack_weights(model)
        for name, tensor in model.state_dict().items():
            unpacked = np.frombuffer(base64.b64decode(packed[name]), dtype="<f4")
            np.testing.assert_array_equal(unpacked, tensor.detach().numpy().flatten())


def test_digit_test_set_cannot_change_checkpoints_or_validation_choice():
    generator = torch.Generator().manual_seed(2)
    images = torch.randint(0, 256, (40, 28, 28), dtype=torch.uint8, generator=generator)
    labels = torch.arange(40).remainder(10)
    split = prepare_data(images, labels, images[:10], labels[:10], validation_size=10)
    first, _, _ = train_model(
        split, {"id": "fixture", "channels": [2, 2]}, epochs=2, batch_size=16, device="cpu"
    )
    split["test"]["y"] = (split["test"]["y"] + 1).remainder(10)
    second, _, _ = train_model(
        split, {"id": "fixture", "channels": [2, 2]}, epochs=2, batch_size=16, device="cpu"
    )
    assert (
        first["best_epoch"]
        == min(first["history"][1:], key=lambda r: r["validation"]["loss"])["epoch"]
    )
    assert first["best_epoch"] == second["best_epoch"]
    for before, after in zip(first["history"], second["history"], strict=True):
        assert before["weights"] == after["weights"]
        assert before["validation"] == after["validation"]
        if before["epoch"]:
            assert before["update"]["after"] == before["weights"]["conv1.weight"]
            assert before["update"]["batch_size"] == 14
            assert before["update"]["optimizer_step"] == before["epoch"] * 2
