"""Flask adapter guards: model allowlist and request-size limit."""
import io

import pytest

from main import ModelServerApplication
from src.server.enums import ClientErrorMessage
from src.server.model_allowlist import ALLOWED_MODELS_ENV


@pytest.fixture
def make_client(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    def _make(**env: str):
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        return ModelServerApplication().app.test_client()

    return _make


def test_spec_rejects_disallowed_model(make_client):
    client = make_client(**{ALLOWED_MODELS_ENV: "df_default"})
    response = client.get("/spec?model=attacker_model")
    assert response.status_code == 400
    assert response.get_json()["error"] == ClientErrorMessage.MODEL_NOT_ALLOWED.value


def test_run_rejects_disallowed_model(make_client):
    client = make_client(**{ALLOWED_MODELS_ENV: "df_default"})
    response = client.post(
        "/run",
        data={"model": "attacker_model", "file": (io.BytesIO(b"png"), "x.png", "image/png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_run_rejects_oversized_body_with_413(make_client):
    client = make_client(MAX_CONTENT_LENGTH_BYTES="64")
    response = client.post(
        "/run",
        data={"model": "df_default", "file": (io.BytesIO(b"x" * 128), "x.png", "image/png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 413
