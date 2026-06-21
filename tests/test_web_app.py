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


# --- Guards: body size limit -------------------------------------------------

def test_run_rejects_oversized_body_with_413():
    # Arrange: a tiny limit so any real multipart body exceeds it.
    ctx = MagicMock()
    client = TestClient(build_api(ctx, max_request_bytes=5))

    # Act
    resp = client.post(
        "/run",
        files={"file": ("x.png", b"way more than five bytes", "image/png")},
        data={"model": "df_default"},
    )

    # Assert: rejected before the route runs, so no GPU work / OOM risk.
    assert resp.status_code == 413
    assert resp.json()["detail"] == "Request body too large"
    ctx.controller.handle_simulation_request.assert_not_called()


# --- Guards: model allowlist -------------------------------------------------

def test_run_rejects_disallowed_model_with_400():
    # Arrange
    ctx = MagicMock()
    client = TestClient(build_api(ctx, allowed_models=("df_default",)))

    # Act
    resp = client.post(
        "/run",
        files={"file": ("x.png", b"img", "image/png")},
        data={"model": "evil_model"},
    )

    # Assert: unknown model never reaches the download-on-demand path.
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Requested model is not available"
    ctx.controller.handle_simulation_request.assert_not_called()


def test_run_allows_listed_model():
    # Arrange
    ctx = MagicMock()
    ctx.controller.handle_simulation_request.return_value = {
        "simulation": [[1.0]], "shape": [1, 1], "status": "success", "error": None,
    }
    client = TestClient(build_api(ctx, allowed_models=("df_default",)))

    # Act
    resp = client.post(
        "/run",
        files={"file": ("x.png", b"img", "image/png")},
        data={"model": "df_default"},
    )

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    ctx.controller.handle_simulation_request.assert_called_once()


def test_spec_rejects_disallowed_model_with_400():
    # Arrange
    ctx = MagicMock()
    client = TestClient(build_api(ctx, allowed_models=("df_default",)))

    # Act
    resp = client.get("/spec", params={"model": "evil_model"})

    # Assert
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Requested model is not available"
    ctx.spec_service.get_spec.assert_not_called()
