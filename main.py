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
from src.server.services.spec_service import SpecServiceFactory
from src.server.enums import LogLevel, ContentType, HTTPStatus, SpecKey, EnvVar


class ModelServerApplication:

    def __init__(self):
        self._app = Flask(__name__)
        self._controller: ModelServerController = None
        self._spec_service = None
        self._setup_dependencies()
        self._setup_routes()

    def _setup_dependencies(self) -> None:
        logger = StructuredLogger("ModelServer", LogLevel.INFO)
        image_processor = ImageProcessorFactory.create_standard_processor(logger)

        # Use 'or' operator to treat empty/whitespace env vars as unset
        model_bucket = os.getenv(EnvVar.MODEL_BUCKET.value) or "daylight-factor"
        model_url_template = os.getenv(
            EnvVar.MODEL_URL_TEMPLATE.value,
            f"https://{model_bucket}.s3.fr-par.scw.cloud/models/{{name}}.onnx"
        )

        if model_url_template.startswith("s3://"):
            access_key = os.getenv(EnvVar.SCW_ACCESS_KEY.value)
            secret_key = os.getenv(EnvVar.SCW_SECRET_KEY.value)
            if not access_key or not secret_key:
                raise EnvironmentError(f"{EnvVar.SCW_ACCESS_KEY.value} and {EnvVar.SCW_SECRET_KEY.value} must be set when MODEL_URL_TEMPLATE uses s3://")
            download_strategy = S3DownloadStrategy(
                logger=logger,
                access_key=access_key,
                secret_key=secret_key,
                region=os.getenv(EnvVar.SCW_REGION.value, "fr-par"),
                endpoint_url=os.getenv(EnvVar.SCW_ENDPOINT_URL.value, "https://s3.fr-par.scw.cloud"),
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

        spec_url_template = os.getenv(
            EnvVar.SPEC_URL_TEMPLATE.value,
            f"s3://{model_bucket}/{{name}}/spec.json"
        )
        if spec_url_template.startswith("s3://"):
            spec_access_key = os.getenv(EnvVar.SCW_ACCESS_KEY.value)
            spec_secret_key = os.getenv(EnvVar.SCW_SECRET_KEY.value)
            if not spec_access_key or not spec_secret_key:
                raise EnvironmentError(f"{EnvVar.SCW_ACCESS_KEY.value} and {EnvVar.SCW_SECRET_KEY.value} must be set when SPEC_URL_TEMPLATE uses s3://")
            spec_download_strategy = S3DownloadStrategy(
                logger=logger,
                access_key=spec_access_key,
                secret_key=spec_secret_key,
                region=os.getenv(EnvVar.SCW_REGION.value, "fr-par"),
                endpoint_url=os.getenv(EnvVar.SCW_ENDPOINT_URL.value, "https://s3.fr-par.scw.cloud"),
            )
        else:
            spec_download_strategy = HTTPDownloadStrategy(logger)

        self._spec_service = SpecServiceFactory.create(
            checkpoints_dir="./checkpoints",
            download_strategy=spec_download_strategy,
            logger=logger,
            spec_url_template=spec_url_template,
        )

        self._controller = ModelServerController(simulation_service=simulation_service, logger=logger)
        self._controller.initialize()

    def _setup_routes(self) -> None:
        self._app.add_url_rule("/", "get_status", self._get_status, methods=["GET"])
        self._app.add_url_rule("/run", "run_simulation", self._run_simulation, methods=["POST"])
        self._app.add_url_rule("/spec", "get_spec", self._get_spec, methods=["GET"])

    def _get_status(self) -> Dict[str, Any]:
        return jsonify(self._controller.get_status())

    def _get_spec(self) -> Dict[str, Any]:
        model_name = request.args.get("model")
        if not model_name:
            return jsonify({"error": "'model' query parameter is required"}), HTTPStatus.BAD_REQUEST.value
        try:
            spec = self._spec_service.get_spec(model_name)
            return jsonify({
                "encoding_scheme": spec.get(SpecKey.ARCHITECTURE.value, {}).get(SpecKey.ENCODING_VERSION.value),
                "encoder_model_type": spec.get(SpecKey.TRAINING.value, {}).get(SpecKey.TARGET.value),
            })
        except Exception:
            self._app.logger.exception("Failed to retrieve spec for model '%s'", model_name)
            return jsonify({"error": "Failed to retrieve spec"}), HTTPStatus.INTERNAL_SERVER_ERROR.value

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
