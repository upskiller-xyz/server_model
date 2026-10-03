"""Unit tests for deploy-time config parsing (modal_app.config)."""
import importlib

import pytest

import modal_app.config as config
from modal_app.config import _parse_allowed_models, _DEFAULT_ALLOWED_MODELS


@pytest.fixture
def reload_config(monkeypatch):
    """Re-import the module so its env-driven module-level values are re-read.

    The reload is undone afterwards so the imported module never carries a
    test's environment into later tests.
    """
    yield lambda: importlib.reload(config)
    monkeypatch.undo()
    importlib.reload(config)


def test_runtime_env_forwards_checksum_settings(monkeypatch, reload_config):
    # Arrange: deploy-time checksum settings must reach the runtime container.
    monkeypatch.setenv("MODEL_SHA256", '{"m.onnx": "abc"}')
    monkeypatch.setenv("MODEL_SHA256_REQUIRED", "true")

    # Act
    fresh = reload_config()

    # Assert: the registry pins and the required flag are forwarded.
    assert fresh.RUNTIME_ENV["MODEL_SHA256"] == '{"m.onnx": "abc"}'
    assert fresh.RUNTIME_ENV["MODEL_SHA256_REQUIRED"] == "true"
    assert "ALLOWED_MODELS" in fresh.RUNTIME_ENV


def test_runtime_env_defaults_when_checksum_unset(monkeypatch, reload_config):
    # Arrange
    monkeypatch.delenv("MODEL_SHA256", raising=False)
    monkeypatch.delenv("MODEL_SHA256_REQUIRED", raising=False)

    # Act
    fresh = reload_config()

    # Assert: absent pins forward as empty / not-required, never crash.
    assert fresh.RUNTIME_ENV["MODEL_SHA256"] == ""
    assert fresh.RUNTIME_ENV["MODEL_SHA256_REQUIRED"] == "false"


def test_allowed_models_defaults_when_env_unset():
    # Arrange / Act
    from_none = _parse_allowed_models(None)
    from_empty = _parse_allowed_models("")

    # Assert
    assert from_none == _DEFAULT_ALLOWED_MODELS
    assert from_empty == _DEFAULT_ALLOWED_MODELS


def test_allowed_models_parsed_from_csv_and_trimmed():
    # Arrange
    raw = "a, b ,c"

    # Act
    parsed = _parse_allowed_models(raw)

    # Assert
    assert parsed == ("a", "b", "c")


def test_allowed_models_falls_back_when_only_separators():
    # Arrange: a string of only commas/whitespace yields no names.
    raw = " , , "

    # Act
    parsed = _parse_allowed_models(raw)

    # Assert: keep the default rather than serving nothing.
    assert parsed == _DEFAULT_ALLOWED_MODELS
