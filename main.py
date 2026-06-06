import numpy as np
import requests
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional

from src.server.bootstrap import ServerBootstrap
from src.server.cond_vec import CondVecParser
from src.server.controller import ModelServerController
from src.server.enums import ContentType, HTTPStatus, SpecKey


class ModelServerApplication:

    def __init__(self):
        self._app = Flask(__name__)
        self._controller: ModelServerController = None
        self._spec_service = None
        self._setup_dependencies()
        self._setup_routes()

    def _setup_dependencies(self) -> None:
        bootstrap = ServerBootstrap.from_env(checkpoints_dir="./checkpoints")
        self._controller = bootstrap.controller
        self._spec_service = bootstrap.spec_service

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
        except (ClientError, FileNotFoundError, requests.exceptions.HTTPError) as e:
            is_404 = (
                (isinstance(e, ClientError) and e.response["Error"]["Code"] == "404")
                or (isinstance(e, requests.exceptions.HTTPError) and e.response is not None and e.response.status_code == 404)
            )
            if is_404:
                return jsonify({"error": f"spec.json not found for model '{model_name}'"}), 404
            self._app.logger.exception("Failed to retrieve spec for model '%s'", model_name)
            return jsonify({"error": "Failed to retrieve spec"}), HTTPStatus.INTERNAL_SERVER_ERROR.value
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
        try:
            cond_vec: Optional[np.ndarray] = CondVecParser.parse(request.form.get('cond_vec'))
        except ValueError as e:
            raise BadRequest(str(e))

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
