"""Unit tests for the model server's FastAPI routes (build_api).

Tests the routes via a plain FastAPI TestClient with a stub ctx — no Modal runtime.
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from modal_app.app import build_api


def test_warm_returns_ok_without_touching_ctx():
    # /warm must be cheap: it does no inference and ignores ctx (the container is
    # already warm by the time a route is served). A MagicMock ctx is never used.
    client = TestClient(build_api(MagicMock()))
    resp = client.get("/warm")
    assert resp.status_code == 200
    assert resp.json() == {"warm": True}


def test_status_delegates_to_controller():
    ctx = MagicMock()
    ctx.controller.get_status.return_value = {"name": "x", "status": "running"}
    client = TestClient(build_api(ctx))
    resp = client.get("/status")
    assert resp.status_code == 200
    assert resp.json() == {"name": "x", "status": "running"}
    ctx.controller.get_status.assert_called_once()
