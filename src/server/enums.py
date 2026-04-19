from enum import Enum


class ModelStatus(Enum):
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class ServerStatus(Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ContentType(Enum):
    IMAGE_JPEG = "image/jpeg"
    IMAGE_PNG = "image/png"
    IMAGE_WEBP = "image/webp"
    IMAGE_BMP = "image/bmp"

    @classmethod
    def is_image(cls, content_type: str) -> bool:
        return content_type.startswith('image/')


class HTTPStatus(Enum):
    OK = 200
    BAD_REQUEST = 400
    INTERNAL_SERVER_ERROR = 500


class SpecKey(Enum):
    """Keys used in spec.json files."""
    ARCHITECTURE = "architecture"
    TRAINING = "training"
    ENCODING_VERSION = "encoding_version"
    TARGET = "target"


class EnvVar(Enum):
    """Environment variable names."""
    MODEL_BUCKET = "MODEL_BUCKET"
    MODEL_URL_TEMPLATE = "MODEL_URL_TEMPLATE"
    SPEC_URL_TEMPLATE = "SPEC_URL_TEMPLATE"
    SCW_ACCESS_KEY = "SCW_ACCESS_KEY"
    SCW_SECRET_KEY = "SCW_SECRET_KEY"
    SCW_REGION = "SCW_REGION"
    SCW_ENDPOINT_URL = "SCW_ENDPOINT_URL"