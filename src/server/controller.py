from typing import Dict, Any, Optional
import numpy as np
from .interfaces import IServerController, ISimulationService, ILogger
from .enums import ServerStatus, ClientErrorMessage
from .schemas import SimulationResponse


class ModelServerController(IServerController):

    def __init__(
        self,
        simulation_service: ISimulationService,
        logger: ILogger,
        name: str = "Upskiller Model Server",
        version: str = "2.0.0",
    ):
        self._simulation_service = simulation_service
        self._logger = logger
        self._name = name
        self._version = version
        self._status = ServerStatus.STARTING

    def initialize(self) -> None:
        self._status = ServerStatus.RUNNING
        self._logger.info("Server controller initialized")

    def get_status(self) -> Dict[str, Any]:
        return {"name": self._name, "version": self._version, "status": self._status.value}

    def preload_model(self, model_name: str) -> None:
        """Warm a model's session ahead of the first request."""
        self._simulation_service.preload(model_name)

    def handle_simulation_request(
        self,
        image_bytes: bytes,
        model_name: str,
        cond_vec: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        try:
            return self._simulation_service.simulate(image_bytes, model_name, cond_vec)
        except Exception as e:
            self._logger.error(f"Simulation request failed: {e}")
            return SimulationResponse.failure(ClientErrorMessage.SIMULATION_FAILED).to_dict()

    @property
    def status(self) -> ServerStatus:
        return self._status

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version
