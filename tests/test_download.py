"""Unit tests for atomic, checksum-verified artifact downloads."""
import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from src.server.services.download import (
    ArtifactIntegrityError,
    AtomicDownloadStrategy,
    ChecksumRegistry,
    ChecksumVerifier,
    HTTPDownloadStrategy,
)

PAYLOAD = b"onnx-bytes"
PAYLOAD_SHA256 = hashlib.sha256(PAYLOAD).hexdigest()


class _FakeStrategy(AtomicDownloadStrategy):
    """Writes a fixed payload, or fails mid-transfer."""

    def __init__(self, logger, verifier=None, payload: bytes = PAYLOAD, fail: bool = False):
        super().__init__(logger, verifier)
        self._payload = payload
        self._fail = fail
        self.calls = 0

    def _fetch(self, url: str, tmp_path: str) -> None:
        self.calls += 1
        Path(tmp_path).write_bytes(self._payload[:3])
        if self._fail:
            raise IOError("connection reset")
        Path(tmp_path).write_bytes(self._payload)


def _leftovers(directory: Path) -> list:
    return [p.name for p in directory.iterdir()]


class TestAtomicDownload:

    def test_success_moves_file_into_place(self, tmp_path):
        target = tmp_path / "m.onnx"
        _FakeStrategy(MagicMock()).download("u", str(target))
        assert target.read_bytes() == PAYLOAD
        assert _leftovers(tmp_path) == ["m.onnx"]

    def test_failed_transfer_leaves_no_partial_file(self, tmp_path):
        target = tmp_path / "m.onnx"
        with pytest.raises(IOError):
            _FakeStrategy(MagicMock(), fail=True).download("u", str(target))
        assert _leftovers(tmp_path) == []

    def test_existing_file_is_not_refetched(self, tmp_path):
        target = tmp_path / "m.onnx"
        target.write_bytes(b"cached")
        strategy = _FakeStrategy(MagicMock())
        strategy.download("u", str(target))
        assert strategy.calls == 0


class TestChecksumVerification:

    @staticmethod
    def _verifier(digests: dict, required: bool = False) -> ChecksumVerifier:
        return ChecksumVerifier(ChecksumRegistry(digests, required), MagicMock())

    def test_matching_digest_is_accepted(self, tmp_path):
        target = tmp_path / "m.onnx"
        _FakeStrategy(MagicMock(), self._verifier({"m.onnx": PAYLOAD_SHA256.upper()})).download("u", str(target))
        assert target.read_bytes() == PAYLOAD

    def test_mismatching_digest_is_rejected_and_not_cached(self, tmp_path):
        target = tmp_path / "m.onnx"
        with pytest.raises(ArtifactIntegrityError):
            _FakeStrategy(MagicMock(), self._verifier({"m.onnx": "0" * 64})).download("u", str(target))
        assert _leftovers(tmp_path) == []

    def test_unpinned_file_is_allowed_when_not_required(self, tmp_path):
        target = tmp_path / "m.onnx"
        _FakeStrategy(MagicMock(), self._verifier({})).download("u", str(target))
        assert target.exists()

    def test_unpinned_file_is_refused_before_transfer_when_required(self, tmp_path):
        strategy = _FakeStrategy(MagicMock(), self._verifier({}, required=True))
        with pytest.raises(ArtifactIntegrityError):
            strategy.download("u", str(tmp_path / "m.onnx"))
        assert strategy.calls == 0


class TestChecksumRegistry:

    def test_from_json_empty_means_no_pins(self):
        assert ChecksumRegistry.from_json("").expected("m.onnx") is None
        assert ChecksumRegistry.from_json(None).expected("m.onnx") is None

    def test_from_json_parses_pins(self):
        registry = ChecksumRegistry.from_json('{"m.onnx": " ABC "}', required=True)
        assert registry.expected("m.onnx") == "abc"
        assert registry.required is True

    @pytest.mark.parametrize("raw", ['["m.onnx"]', '{"m.onnx": 1}', "not json"])
    def test_from_json_rejects_malformed(self, raw):
        with pytest.raises(ValueError):
            ChecksumRegistry.from_json(raw)


class TestHTTPDownloadStrategy:

    def test_uses_timeout_and_cleans_up_on_http_error(self, tmp_path, monkeypatch):
        response = MagicMock()
        response.__enter__.return_value = response
        response.raise_for_status.side_effect = requests.HTTPError("404")
        get = MagicMock(return_value=response)
        monkeypatch.setattr(requests, "get", get)

        with pytest.raises(requests.HTTPError):
            HTTPDownloadStrategy(MagicMock()).download("https://h/m.onnx", str(tmp_path / "m.onnx"))

        assert get.call_args.kwargs["timeout"] is not None
        assert _leftovers(tmp_path) == []
