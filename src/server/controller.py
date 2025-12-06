from typing import Dict, Any
from .interfaces import IServerController, IPredictionService, ILogger
from .enums import ServerStatus, HTTPStatus


class ModelServerController(IServerController):
    """Main server controller implementing dependency injection"""

    def __init__(
        self,
        prediction_service: IPredictionService,
        logger: ILogger,
        name: str = "Upskiller Model Server",
        version: str = "2.0.0"
    ):
        self._prediction_service = prediction_service
        self._logger = logger
        self._name = name
        self._version = version
        self._status = ServerStatus.STARTING

    def initialize(self) -> None:
        """Initialize the server"""
        try:
            self._logger.info("Initializing server controller")
            self._status = ServerStatus.RUNNING
            self._logger.info("Server controller initialized successfully")
        except Exception as e:
            self._status = ServerStatus.ERROR
            self._logger.error(f"Server initialization failed: {str(e)}")
            raise

    def get_status(self) -> Dict[str, Any]:
        """Get server status information"""
        return {
            "name": self._name,
            "version": self._version,
            "status": self._status.value
        }

    def handle_prediction_request(self, image_bytes: bytes) -> Dict[str, Any]:
        """Handle prediction request"""
        try:
            self._logger.info("Processing prediction request")
            result = self._prediction_service.predict(image_bytes)
            self._logger.info("Prediction request completed successfully")
            return result
        except Exception as e:
            self._logger.error(f"Prediction request failed: {str(e)}")
            return {
                "prediction": None,
                "shape": None,
                "status": "error",
                "error": str(e)
            }

    @property
    def status(self) -> ServerStatus:
        """Get current server status"""
        return self._status

    @property
    def name(self) -> str:
        """Get server name"""
        return self._name

    @property
    def version(self) -> str:
        """Get server version"""
        return self._version