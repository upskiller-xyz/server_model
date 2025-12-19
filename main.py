from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest
from typing import Dict, Any

from src.server.controller import ModelServerController
from src.server.services.logging import StructuredLogger
from src.server.services.download import HTTPDownloadStrategy
from src.server.services.model_loader import ModelLoaderFactory
from src.server.services.image_processor import ImageProcessorFactory
from src.server.services.simulation import PredictionServiceFactory
from src.server.enums import LogLevel, ContentType, HTTPStatus


class ModelServerApplication:
    """Main application class implementing dependency injection and OOP principles"""

    def __init__(self):
        self._app = Flask(__name__)
        self._controller: ModelServerController = None
        self._setup_dependencies()
        self._setup_routes()

    def _setup_dependencies(self) -> None:
        """Setup all dependencies using dependency injection"""
        # Logger
        logger = StructuredLogger("ModelServer", LogLevel.INFO)

        # Download strategy
        download_strategy = HTTPDownloadStrategy(logger)

        # Model configuration (hardcoded)
        model_name = "df_default_2.0.1"
        model_format = "onnx"
        extension = "onnx"

        # Create model loader
        logger.info(f"Creating ONNX model loader for {model_name}")
        model_loader = ModelLoaderFactory.create_loader(
            model_format,
            model_url=f"https://daylight-factor.s3.fr-par.scw.cloud/models/{model_name}.{extension}",
            local_path=f"./checkpoints/{model_name}.{extension}",
            download_strategy=download_strategy,
            logger=logger
        )

        # Image processor
        image_processor = ImageProcessorFactory.create_standard_processor(logger)

        # Prediction service
        simulation_service = PredictionServiceFactory.create_model_simulation_service(
            model_loader=model_loader,
            image_processor=image_processor,
            logger=logger
        )

        # Controller
        self._controller = ModelServerController(
            simulation_service=simulation_service,
            logger=logger
        )

        # Initialize controller
        self._controller.initialize()

    def _setup_routes(self) -> None:
        """Setup Flask routes"""
        self._app.add_url_rule("/", "get_status", self._get_status, methods=["GET"])
        self._app.add_url_rule("/run", "run_simulation", self._run_simulation, methods=["POST"])

    def _get_status(self) -> Dict[str, Any]:
        """Get server status endpoint"""
        return jsonify(self._controller.get_status())

    def _run_simulation(self) -> Dict[str, Any]:
        """Run simulation endpoint"""
        # Check if file was uploaded
        if 'file' not in request.files:
            raise BadRequest("No file uploaded")

        file = request.files['file']

        # Validate content type
        if not ContentType.is_image(file.content_type):
            raise BadRequest("File must be an image")

        try:
            # Read image bytes
            image_bytes = file.read()

            # Process simulation
            result = self._controller.handle_simulation_request(image_bytes)

            # Check for errors
            if result.get("status") == "error":
                return jsonify(result), HTTPStatus.INTERNAL_SERVER_ERROR.value

            return jsonify(result)

        except Exception as e:
            return jsonify({"error": f"Prediction failed: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR.value

    @property
    def app(self) -> Flask:
        """Get Flask application instance"""
        return self._app


class ServerLauncher:
    """Launcher class for the server application"""

    @staticmethod
    def create_application() -> ModelServerApplication:
        """Create and configure the application"""
        return ModelServerApplication()

    @staticmethod
    def run_server(app: ModelServerApplication, host: str = "0.0.0.0", port: int = 8000) -> None:
        """Run the server"""
        app.app.run(host=host, port=port, debug=False)


def main() -> None:
    """Main entry point"""
    launcher = ServerLauncher()
    application = launcher.create_application()
    launcher.run_server(application)


# Create application instance for gunicorn
application = ModelServerApplication()
app = application.app

if __name__ == "__main__":
    main()