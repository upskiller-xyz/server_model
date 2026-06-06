"""Parsing of the optional cond_vec request field.

Shared by every adapter (Flask, Modal) so the parsing rules live in one place
and stay framework-agnostic — adapters translate ValueError into their own HTTP
error type.
"""
import json
from typing import Optional

import numpy as np


class CondVecParser:
    """Parses the raw cond_vec form field into a (1, D) float32 array."""

    @classmethod
    def parse(cls, raw: Optional[str]) -> Optional[np.ndarray]:
        """Return a (1, D) array for a JSON number array, or None if unset.

        Raises:
            ValueError: if raw is present but not a JSON array of numbers.
        """
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError("'cond_vec' is not valid JSON") from e
        if not isinstance(parsed, list) or not all(isinstance(v, (int, float)) for v in parsed):
            raise ValueError("'cond_vec' must be a JSON array of numbers")
        return np.array(parsed, dtype=np.float32)[np.newaxis, :]
