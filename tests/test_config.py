"""Unit tests for deploy-time config parsing (modal_app.config)."""
from modal_app.config import _parse_allowed_models, _DEFAULT_ALLOWED_MODELS


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
