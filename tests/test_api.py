"""Basic API tests for replay mode."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create test client."""
    import os
    import shutil

    os.environ["MODE"] = "replay"
    from sqlrouter.serve import main

    main._request_history.clear()
    artifacts = tmp_path / "artifacts"
    shutil.copytree(main.settings.artifacts, artifacts)
    monkeypatch.setattr(main.settings, "artifacts", artifacts)
    monkeypatch.setattr(main.settings, "mode", "replay")

    with TestClient(main.app) as test_client:
        response = test_client.post(
            "/api/auth/register",
            json={"email": "tester@example.com", "password": "correct horse battery"},
        )
        assert response.status_code == 201, response.text
        test_client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        yield test_client


def test_health(client):
    """Test health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "replay"


def test_private_api_rejects_requests_without_a_session(client):
    client.headers.pop("Authorization")
    response = client.get("/api/databases")
    assert response.status_code == 401


def test_cors_preflight_is_not_blocked_by_authentication(client):
    client.headers.pop("Authorization")
    response = client.options(
        "/api/databases",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_registration_login_and_logout(client):
    client.headers.pop("Authorization")
    duplicate = client.post(
        "/api/auth/register",
        json={"email": "tester@example.com", "password": "correct horse battery"},
    )
    assert duplicate.status_code == 409

    weak_password = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "short"},
    )
    assert weak_password.status_code == 422

    login = client.post(
        "/api/auth/login",
        json={"email": "TESTER@example.com", "password": "correct horse battery"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    assert client.get("/api/auth/me").json()["email"] == "tester@example.com"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_config(client):
    """Test config endpoint."""
    response = client.get("/api/config")
    assert response.status_code == 200
    
    data = response.json()
    assert "threshold" in data
    assert "layer" in data
    assert data["mode"] == "replay"


def test_databases(client):
    """Test databases endpoint."""
    response = client.get("/api/databases")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    if len(data) > 0:
        db = data[0]
        assert "db_id" in db
        assert "schema" in db


def test_benchmark_questions(client):
    """Test benchmark questions endpoint."""
    response = client.get("/api/benchmark/questions?limit=10")
    assert response.status_code == 200
    
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_metrics(client):
    """Test metrics endpoint."""
    # Test valid metric
    response = client.get("/api/metrics/summary")
    assert response.status_code == 200
    
    data = response.json()
    assert "n_test" in data or "message" in data  # May not exist yet
    
    # Test invalid metric
    response = client.get("/api/metrics/invalid")
    assert response.status_code == 400


def test_route_invalid_db(client):
    """Test routing with invalid database."""
    response = client.post(
        "/api/route",
        json={"db_id": "../etc/passwd", "question": "test", "mode": "auto"},
    )
    assert response.status_code == 422  # Validation error


def test_route_unknown_db(client):
    """Test routing with unknown database."""
    response = client.post(
        "/api/route",
        json={"db_id": "nonexistent", "question": "test", "mode": "auto"},
    )
    # Should fail with 400 or 404
    assert response.status_code in [400, 404]


def test_route_limits_conversation_context_to_four_turns(client):
    response = client.post(
        "/api/route",
        json={
            "db_id": "testdb",
            "question": "Follow up question",
            "context": [
                {"question": f"Question {index}", "sql": "SELECT 1"}
                for index in range(5)
            ],
        },
    )

    assert response.status_code == 422


def test_evaluation_compares_models_and_router(client):
    from sqlrouter.serve import main

    threshold = main.state["store"].get_config()["threshold"]
    main.state["store"].questions = [
        {
            "score_sep": max(0.0, threshold - 0.1),
            "local_ok": True,
            "api_ok": False,
        },
        {
            "score_sep": min(1.0, threshold + 0.1),
            "local_ok": False,
            "api_ok": True,
        },
    ]

    response = client.get("/api/evaluation")

    assert response.status_code == 200
    result = response.json()
    assert result["sample_count"] == 2
    assert result["local_accuracy"] == 50.0
    assert result["api_accuracy"] == 50.0
    assert result["routed_accuracy"] == 100.0
    assert result["api_route_percent"] == 50.0
    assert 0 <= result["estimated_cost_savings_percent"] <= 100
