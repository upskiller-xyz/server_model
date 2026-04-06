import json
import numpy as np
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest
from typing import Dict, Any, Optional

from src.server.controller import ModelServerController
from src.server.services.logging import StructuredLogger
from src.server.services.download import HTTPDownloadStrategy
from src.server.services.image_processor import ImageProcessorFactory
from src.server.services.simulation import SimulationServiceFactory
from src.server.enums import LogLevel, ContentType, HTTPStatus


class ModelServerApplication:

    def __init__(self):
        self._app = Flask(__name__)
        self._controller: ModelServerController = None
        self._setup_dependencies()
        self._setup_routes()

    def _setup_dependencies(self) -> None:
        logger = StructuredLogger("ModelServer", LogLevel.INFO)
        download_strategy = HTTPDownloadStrategy(logger)
        image_processor = ImageProcessorFactory.create_standard_processor(logger)

        simulation_service = SimulationServiceFactory.create(
            checkpoints_dir="./checkpoints",
            download_strategy=download_strategy,
            image_processor=image_processor,
            logger=logger,
        )

        self._controller = ModelServerController(simulation_service=simulation_service, logger=logger)
        self._controller.initialize()

    def _setup_routes(self) -> None:
        self._app.add_url_rule("/", "get_status", self._get_status, methods=["GET"])
        self._app.add_url_rule("/run", "run_simulation", self._run_simulation, methods=["POST"])

    def _get_status(self) -> Dict[str, Any]:
        return jsonify(self._controller.get_status())

    def _run_simulation(self) -> Dict[str, Any]:
        if 'file' not in request.files:
            raise BadRequest("No file uploaded")

        file = request.files['file']
        if not ContentType.is_image(file.content_type):
            raise BadRequest("File must be an image")

        model_name = request.form.get('model')
        if not model_name:
            raise BadRequest("'model' form field is required (e.g. 'df_default_2.0.1')")

        # Optional cond_vec for V5 models — JSON array, e.g. "[0.5, 0.3, 0.8, 0.6, 0.9, 0.4]"
        cond_vec: Optional[np.ndarray] = None
        raw_cond = request.form.get('cond_vec')
        if raw_cond:
            cond_vec = np.array(json.loads(raw_cond), dtype=np.float32)[np.newaxis, :]  # (1, D)

        image_bytes = file.read()
        result = self._controller.handle_simulation_request(image_bytes, model_name, cond_vec)

        if result.get("status") == "error":
            return jsonify(result), HTTPStatus.INTERNAL_SERVER_ERROR.value

        return jsonify(result)

    @property
    def app(self) -> Flask:
        return self._app


# gunicorn entry point
application = ModelServerApplication()
app = application.app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
