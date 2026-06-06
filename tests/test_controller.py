"""Unit tests for ModelServerController."""
from unittest.mock import MagicMock

from src.server.controller import ModelServerController
from src.server.enums import ServerStatus


class TestModelServerController:

    def setup_method(self):
        self.simulation_service = MagicMock()
        self.logger = MagicMock()
        self.controller = ModelServerController(
            simulation_service=self.simulation_service,
            logger=self.logger,
        )

    def test_preload_model_delegates_to_service(self):
        self.controller.preload_model("df_default_2.0.1")
        self.simulation_service.preload.assert_called_once_with("df_default_2.0.1")

    def test_handle_simulation_request_delegates(self):
        self.simulation_service.simulate.return_value = {"status": "success"}
        result = self.controller.handle_simulation_request(b"img", "model", None)
        self.simulation_service.simulate.assert_called_once_with(b"img", "model", None)
        assert result == {"status": "success"}

    def test_handle_simulation_request_wraps_exceptions(self):
        self.simulation_service.simulate.side_effect = RuntimeError("boom")
        result = self.controller.handle_simulation_request(b"img", "model", None)
        assert result["status"] == "error"
        assert "boom" in result["error"]

    def test_initialize_sets_running_status(self):
        self.controller.initialize()
        assert self.controller.status == ServerStatus.RUNNING
        assert self.controller.get_status()["status"] == ServerStatus.RUNNING.value
