"""Tests for the serving layer (FastAPI app + CLI)."""

import json

from fastapi.testclient import TestClient
from serve.app import create_app
from serve.train import train_pipeline


def test_health_and_predict():
    app = create_app(model=train_pipeline(seed=0))
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}

    # A 1st-class woman: high survival probability in the synthetic model.
    r = client.post(
        "/predict",
        json={"pclass": 1, "sex": "female", "age": 30, "sibsp": 0, "parch": 0, "fare": 100, "embarked": "C"},
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"survived", "probability"}
    assert 0.0 <= body["probability"] <= 1.0
    assert body["survived"] == 1


def test_predict_handles_missing_age():
    app = create_app(model=train_pipeline(seed=0))
    client = TestClient(app)
    # age omitted (None) — the pipeline's imputer must handle it.
    r = client.post("/predict", json={"pclass": 3, "sex": "male", "fare": 7.5})
    assert r.status_code == 200
    assert 0.0 <= r.json()["probability"] <= 1.0


def test_cli(capsys):
    from serve import cli

    cli.main(["--pclass", "1", "--sex", "female", "--fare", "100", "--embarked", "C"])
    out = json.loads(capsys.readouterr().out)
    assert set(out) == {"survived", "probability"}
    assert out["survived"] == 1
