import json
import os
import numpy as np
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest
from typing import Dict, Any, Optional

from src.server.controller import ModelServerController
from src.server.services.logging import StructuredLogger
from src.server.services.download import HTTPDownloadStrategy, S3DownloadStrategy
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
        image_processor = ImageProcessorFactory.create_standard_processor(logger)

        model_bucket = os.getenv("MODEL_BUCKET", "daylight-factor")
        model_url_template = os.getenv(
            "MODEL_URL_TEMPLATE",
            f"https://{model_bucket}.s3.fr-par.scw.cloud/models/{{name}}.onnx"
        )

        if model_url_template.startswith("s3://"):
            access_key = os.getenv("SCW_ACCESS_KEY")
            secret_key = os.getenv("SCW_SECRET_KEY")
            if not access_key or not secret_key:
                raise EnvironmentError("SCW_ACCESS_KEY and SCW_SECRET_KEY must be set when MODEL_URL_TEMPLATE uses s3://")
            download_strategy = S3DownloadStrategy(
                logger=logger,
                access_key=access_key,
                secret_key=secret_key,
                region=os.getenv("SCW_REGION", "fr-par"),
                endpoint_url=os.getenv("SCW_ENDPOINT_URL", "https://s3.fr-par.scw.cloud"),
            )
        else:
            download_strategy = HTTPDownloadStrategy(logger)

        simulation_service = SimulationServiceFactory.create(
            checkpoints_dir="./checkpoints",
            download_strategy=download_strategy,
            image_processor=image_processor,
            logger=logger,
            model_url_template=model_url_template,
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
            try:
                parsed = json.loads(raw_cond)
                if not isinstance(parsed, list) or not all(isinstance(v, (int, float)) for v in parsed):
                    raise BadRequest("'cond_vec' must be a JSON array of numbers")
                cond_vec = np.array(parsed, dtype=np.float32)[np.newaxis, :]  # (1, D)
            except json.JSONDecodeError:
                raise BadRequest("'cond_vec' is not valid JSON")

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
