"""Framework-neutral allowlist of model names a deployment will serve.

/run and /spec fetch by model name and fall back to download-on-demand, so an
unrestricted name lets a caller trigger arbitrary registry fetches. Shared by the
Flask app and the Modal adapter (modal_app/guards.py) so both enforce one list.
"""
import os
from typing import Iterable, Optional

ALLOWED_MODELS_ENV = "ALLOWED_MODELS"

DEFAULT_ALLOWED_MODELS: tuple[str, ...] = (
    "df_default",
    "df_default_2.0.1",
    "df_default_2.0.2",
)


class ModelNameAllowlist:
    """Set of permitted model names."""

    def __init__(self, allowed: Iterable[str]) -> None:
        self._allowed = frozenset(allowed)

    @staticmethod
    def parse(raw: Optional[str]) -> tuple[str, ...]:
        """Parse a comma-separated list, falling back to ``DEFAULT_ALLOWED_MODELS``."""
        if not raw:
            return DEFAULT_ALLOWED_MODELS
        names = tuple(name.strip() for name in raw.split(",") if name.strip())
        return names or DEFAULT_ALLOWED_MODELS

    @classmethod
    def from_environment(cls) -> "ModelNameAllowlist":
        return cls(cls.parse(os.getenv(ALLOWED_MODELS_ENV)))

    def is_allowed(self, model_name: str) -> bool:
        return model_name in self._allowed
