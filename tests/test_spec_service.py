"""Unit tests for ModelSpecService"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from src.server.services.spec_service import ModelSpecService, SpecServiceFactory
from src.server.enums import SpecKey


VALID_SPEC = {
    "architecture": {"encoding_version": "v5"},
    "training": {"target": "df_default"},
}


class TestModelSpecService:

    def setup_method(self):
        self.logger = MagicMock()
        self.download_strategy = MagicMock()

    def _make_service(self, template="s3://bucket/{name}/spec.json", checkpoints_dir="/tmp/checkpoints"):
        return ModelSpecService(
            checkpoints_dir=checkpoints_dir,
            download_strategy=self.download_strategy,
            logger=self.logger,
            spec_url_template=template,
        )

    def test_invalid_template_raises(self):
        with pytest.raises(ValueError, match="SPEC_URL_TEMPLATE"):
            self._make_service(template="s3://bucket/no-placeholder/spec.json")

    def test_get_spec_downloads_when_not_cached(self, tmp_path):
        service = self._make_service(checkpoints_dir=str(tmp_path))

        spec_file = tmp_path / "my-model.json"

        def fake_download(url, local_path):
            Path(local_path).write_text(json.dumps(VALID_SPEC))

        self.download_strategy.download.side_effect = fake_download

        result = service.get_spec("my-model")

        self.download_strategy.download.assert_called_once_with(
            "s3://bucket/my-model/spec.json", str(spec_file)
        )
        assert result[SpecKey.ARCHITECTURE.value][SpecKey.ENCODING_VERSION.value] == "v5"
        assert result[SpecKey.TRAINING.value][SpecKey.TARGET.value] == "df_default"

    def test_get_spec_uses_cache_when_file_exists(self, tmp_path):
        service = self._make_service(checkpoints_dir=str(tmp_path))
        (tmp_path / "cached-model.json").write_text(json.dumps(VALID_SPEC))

        result = service.get_spec("cached-model")

        self.download_strategy.download.assert_not_called()
        assert result[SpecKey.ARCHITECTURE.value][SpecKey.ENCODING_VERSION.value] == "v5"

    def test_get_spec_url_uses_template(self, tmp_path):
        service = self._make_service(
            template="s3://my-bucket/{name}/spec.json",
            checkpoints_dir=str(tmp_path),
        )

        def fake_download(url, local_path):
            Path(local_path).write_text(json.dumps(VALID_SPEC))

        self.download_strategy.download.side_effect = fake_download
        service.get_spec("019da240-uuid")

        url_called = self.download_strategy.download.call_args[0][0]
        assert url_called == "s3://my-bucket/019da240-uuid/spec.json"


class TestSpecServiceFactory:

    def test_create_returns_model_spec_service(self):
        logger = MagicMock()
        download_strategy = MagicMock()
        service = SpecServiceFactory.create(
            checkpoints_dir="/tmp",
            download_strategy=download_strategy,
            logger=logger,
            spec_url_template="s3://bucket/{name}/spec.json",
        )
        assert isinstance(service, ModelSpecService)
