import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_cors_preflight_allowed_origin():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

def test_cors_disallowed_origin():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://malicious.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # The preflight request is rejected with 400 by CORSMiddleware
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
