"""Unit tests for ServerBootstrap dependency wiring.

Relies on the fake onnxruntime registered in conftest.py.
"""
import pytest
from unittest.mock import MagicMock

from src.server.bootstrap import ServerBootstrap
from src.server.controller import ModelServerController
from src.server.enums import EnvVar, ServerStatus
from src.server.services.download import HTTPDownloadStrategy, S3DownloadStrategy
from src.server.services.simulation import ModelSimulationService
from src.server.services.spec_service import ModelSpecService


class TestBuildDownloadStrategy:

    def test_http_template_returns_http_strategy(self):
        strategy = ServerBootstrap._build_download_strategy(
            "https://host/models/{name}.onnx", MagicMock()
        )
        assert isinstance(strategy, HTTPDownloadStrategy)

    def test_s3_template_with_credentials_returns_s3_strategy(self, monkeypatch):
        monkeypatch.setenv(EnvVar.SCW_ACCESS_KEY.value, "key")
        monkeypatch.setenv(EnvVar.SCW_SECRET_KEY.value, "secret")
        strategy = ServerBootstrap._build_download_strategy(
            "s3://bucket/{name}.onnx", MagicMock()
        )
        assert isinstance(strategy, S3DownloadStrategy)

    def test_s3_template_without_credentials_raises(self, monkeypatch):
        monkeypatch.delenv(EnvVar.SCW_ACCESS_KEY.value, raising=False)
        monkeypatch.delenv(EnvVar.SCW_SECRET_KEY.value, raising=False)
        with pytest.raises(EnvironmentError):
            ServerBootstrap._build_download_strategy("s3://bucket/{name}.onnx", MagicMock())


class TestFromEnv:

    def test_wires_initialized_controller_and_spec_service(self, monkeypatch, tmp_path):
        monkeypatch.setenv(EnvVar.MODEL_URL_TEMPLATE.value, "https://host/models/{name}/model.onnx")
        monkeypatch.setenv(EnvVar.SPEC_URL_TEMPLATE.value, "https://host/models/{name}/spec.json")

        bootstrap = ServerBootstrap.from_env(checkpoints_dir=str(tmp_path))

        assert isinstance(bootstrap.controller, ModelServerController)
        assert isinstance(bootstrap.spec_service, ModelSpecService)
        # Controller is initialized (initialize() was called during wiring).
        assert bootstrap.controller.status == ServerStatus.RUNNING

    def test_derives_spec_url_from_model_template(self, monkeypatch, tmp_path):
        # When SPEC_URL_TEMPLATE is unset it is derived from the model template
        # by replacing the filename with spec.json.
        monkeypatch.setenv(EnvVar.MODEL_URL_TEMPLATE.value, "s3://bucket/{name}/model.onnx")
        monkeypatch.delenv(EnvVar.SPEC_URL_TEMPLATE.value, raising=False)
        monkeypatch.setenv(EnvVar.SCW_ACCESS_KEY.value, "key")
        monkeypatch.setenv(EnvVar.SCW_SECRET_KEY.value, "secret")

        bootstrap = ServerBootstrap.from_env(checkpoints_dir=str(tmp_path))

        assert isinstance(bootstrap.spec_service, ModelSpecService)
        assert bootstrap.spec_service._spec_url_template == "s3://bucket/{name}/spec.json"

    def test_whitespace_env_treated_as_unset(self, monkeypatch, tmp_path):
        # Whitespace-only MODEL_URL_TEMPLATE must fall back to the default,
        # not be used verbatim (which would be an invalid template).
        monkeypatch.setenv(EnvVar.MODEL_URL_TEMPLATE.value, "   ")
        monkeypatch.delenv(EnvVar.SPEC_URL_TEMPLATE.value, raising=False)
        monkeypatch.setenv(EnvVar.MODEL_BUCKET.value, "daylight-factor")

        bootstrap = ServerBootstrap.from_env(checkpoints_dir=str(tmp_path))

        sim = bootstrap.controller._simulation_service
        assert sim._model_url_template == "https://daylight-factor.s3.fr-par.scw.cloud/models/{name}.onnx"

    def test_default_spec_url_preserves_name_for_filename_style_template(self, monkeypatch, tmp_path):
        # Filename-style model template must still derive a spec URL with {name}.
        monkeypatch.setenv(EnvVar.MODEL_URL_TEMPLATE.value, "https://host/models/{name}.onnx")
        monkeypatch.delenv(EnvVar.SPEC_URL_TEMPLATE.value, raising=False)

        bootstrap = ServerBootstrap.from_env(checkpoints_dir=str(tmp_path))

        assert bootstrap.spec_service._spec_url_template == "https://host/models/{name}/spec.json"

    def test_simulation_service_is_model_simulation_service(self, monkeypatch, tmp_path):
        monkeypatch.setenv(EnvVar.MODEL_URL_TEMPLATE.value, "https://host/models/{name}/model.onnx")
        monkeypatch.setenv(EnvVar.SPEC_URL_TEMPLATE.value, "https://host/models/{name}/spec.json")

        bootstrap = ServerBootstrap.from_env(checkpoints_dir=str(tmp_path))

        assert isinstance(bootstrap.controller._simulation_service, ModelSimulationService)
