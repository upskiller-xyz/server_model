"""Response schemas for the model server.

Replaces the ad-hoc result dicts with a typed schema whose keys/values are
driven by enums (no magic strings). ``to_dict()`` produces the wire form returned
to clients; construct via the ``success`` / ``failure`` factories so the two
shapes can never drift apart.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .enums import ResponseKey, ResponseStatus, ClientErrorMessage


@dataclass(frozen=True)
class SimulationResponse:
    """Typed schema for a /run (simulation) response."""

    status: ResponseStatus
    simulation: Optional[List[List[float]]] = None
    shape: Optional[List[int]] = None
    error: Optional[str] = None

    @classmethod
    def success(cls, simulation: List[List[float]], shape: List[int]) -> "SimulationResponse":
        return cls(status=ResponseStatus.SUCCESS, simulation=simulation, shape=shape)

    @classmethod
    def failure(cls, error: ClientErrorMessage) -> "SimulationResponse":
        """Build an error response from a generic, client-safe message enum."""
        return cls(status=ResponseStatus.ERROR, error=error.value)

    @property
    def is_error(self) -> bool:
        return self.status is ResponseStatus.ERROR

    def to_dict(self) -> Dict[str, Any]:
        return {
            ResponseKey.SIMULATION.value: self.simulation,
            ResponseKey.SHAPE.value: self.shape,
            ResponseKey.STATUS.value: self.status.value,
            ResponseKey.ERROR.value: self.error,
        }
