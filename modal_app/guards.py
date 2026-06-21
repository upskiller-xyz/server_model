"""Web-layer guards for the model server's FastAPI app (defense-in-depth).

Modal proxy-auth is the access gate; these guards limit the damage an authorized
(or token-leaked) caller can do once past it:

- :class:`BodySizeLimitMiddleware` rejects oversized uploads before they are read
  into memory on the GPU container (413).
- :class:`ModelAllowlist` restricts which model names ``/run`` and ``/spec`` will
  serve, so an arbitrary name cannot trigger registry fetches outside the
  deployment's intended set (400).
"""
from typing import Iterable

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.server.enums import HTTPStatus, ClientErrorMessage


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose advertised body exceeds ``max_bytes`` with 413.

    Checks ``Content-Length`` so the oversized body is never read into memory
    (multipart uploads to ``/run`` always advertise it). Requests without the
    header pass through to the route, where FastAPI/Modal platform limits still
    apply — this guard targets the realistic OOM/GPU-waste case, not every edge.
    """

    def __init__(self, app, max_bytes: int) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None and content_length.isdigit():
            if int(content_length) > self._max_bytes:
                return JSONResponse(
                    status_code=HTTPStatus.PAYLOAD_TOO_LARGE.value,
                    content={"detail": ClientErrorMessage.PAYLOAD_TOO_LARGE.value},
                )
        return await call_next(request)


class ModelAllowlist:
    """Allowlist of model names the deployment will serve.

    Centralizes the check so both ``/run`` and ``/spec`` enforce the same set.
    Rejects unknown names with 400 rather than letting them reach the
    download-on-demand path with an arbitrary registry URL.
    """

    def __init__(self, allowed: Iterable[str]) -> None:
        self._allowed = frozenset(allowed)

    def is_allowed(self, model_name: str) -> bool:
        return model_name in self._allowed

    def validate(self, model_name: str) -> None:
        """Raise 400 ``HTTPException`` if ``model_name`` is not permitted."""
        if not self.is_allowed(model_name):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST.value,
                detail=ClientErrorMessage.MODEL_NOT_ALLOWED.value,
            )
