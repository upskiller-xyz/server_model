"""Unit tests for web-layer guards (modal_app.guards)."""
import pytest
from fastapi import HTTPException

from modal_app.guards import BodySizeLimitMiddleware, ModelAllowlist


class TestDeclaredLength:
    """Content-Length parsing for the body-size guard."""

    def test_parses_plain_integer(self):
        # Arrange
        header = "1024"

        # Act
        parsed = BodySizeLimitMiddleware._declared_length(header)

        # Assert
        assert parsed == 1024

    def test_tolerates_surrounding_whitespace(self):
        # Arrange: a value that str.isdigit() would reject, bypassing the limit.
        header = " 1024 "

        # Act
        parsed = BodySizeLimitMiddleware._declared_length(header)

        # Assert
        assert parsed == 1024

    def test_returns_none_when_absent(self):
        # Arrange / Act
        parsed = BodySizeLimitMiddleware._declared_length(None)

        # Assert
        assert parsed is None

    def test_returns_none_when_unparsable(self):
        # Arrange / Act
        parsed = BodySizeLimitMiddleware._declared_length("not-a-number")

        # Assert
        assert parsed is None


class TestModelAllowlist:

    def test_listed_model_is_allowed(self):
        # Arrange
        allowlist = ModelAllowlist(("df_default",))

        # Act / Assert
        assert allowlist.is_allowed("df_default") is True
        allowlist.validate("df_default")  # must not raise

    def test_unlisted_model_raises_400(self):
        # Arrange
        allowlist = ModelAllowlist(("df_default",))

        # Act / Assert
        with pytest.raises(HTTPException) as exc:
            allowlist.validate("evil_model")
        assert exc.value.status_code == 400

    def test_empty_allowlist_allows_nothing(self):
        # Arrange: an explicit empty allowlist means "allow none".
        allowlist = ModelAllowlist(())

        # Act / Assert
        assert allowlist.is_allowed("df_default") is False
