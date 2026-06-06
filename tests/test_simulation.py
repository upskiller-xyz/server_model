"""Unit tests for ModelSimulationService model resolution and preloading.

Relies on the fake onnxruntime registered in conftest.py.
"""
import onnxruntime as ort
import pytest
from unittest.mock import MagicMock

from src.server.services.simulation import ModelSimulationService


class TestResolveModelSource:

    def setup_method(self):
        self.download = MagicMock()
        self.logger = MagicMock()

    def _make_service(self, checkpoints_dir):
        return ModelSimulationService(
            checkpoints_dir=str(checkpoints_dir),
            download_strategy=self.download,
            image_processor=MagicMock(),
            logger=self.logger,
            model_url_template="https://host/models/{name}.onnx",
        )

    def test_prefers_optimized_graph_with_optimizations_disabled(self, tmp_path):
        (tmp_path / "model1.opt.onnx").write_bytes(b"opt")
        (tmp_path / "model1.onnx").write_bytes(b"raw")
        service = self._make_service(tmp_path)

        path, level = service._resolve_model_source("model1")

        assert path == tmp_path / "model1.opt.onnx"
        assert level == ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        self.download.download.assert_not_called()

    def test_falls_back_to_raw_with_full_optimization(self, tmp_path):
        (tmp_path / "model1.onnx").write_bytes(b"raw")
        service = self._make_service(tmp_path)

        path, level = service._resolve_model_source("model1")

        assert path == tmp_path / "model1.onnx"
        assert level == ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.download.download.assert_not_called()

    def test_rejects_invalid_model_name(self, tmp_path):
        service = self._make_service(tmp_path)
        with pytest.raises(ValueError):
            service._resolve_model_source("../escape")
        self.download.download.assert_not_called()

    def test_downloads_when_no_local_file(self, tmp_path):
        service = self._make_service(tmp_path)
        expected = tmp_path / "model1.onnx"

        def fake_download(url, local_path):
            open(local_path, "wb").close()

        self.download.download.side_effect = fake_download

        path, level = service._resolve_model_source("model1")

        assert path == expected
        assert level == ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.download.download.assert_called_once_with(
            "https://host/models/model1.onnx", str(expected)
        )


class TestPreload:

    def test_preload_loads_and_caches_once(self, tmp_path):
        service = ModelSimulationService(
            checkpoints_dir=str(tmp_path),
            download_strategy=MagicMock(),
            image_processor=MagicMock(),
            logger=MagicMock(),
            model_url_template="https://host/{name}.onnx",
        )
        sentinel = object()
        service._load_model = MagicMock(return_value=sentinel)

        service.preload("model1")
        service.preload("model1")  # second call hits the cache

        service._load_model.assert_called_once_with("model1")
        assert service._cache["model1"] is sentinel
