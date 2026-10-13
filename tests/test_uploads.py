"""Tests for custom database and CSV uploads."""
import io
import json
import sqlite3
import zipfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def upload_client(tmp_path, monkeypatch):
    from sqlrouter.serve import main

    main._request_history.clear()
    artifacts = tmp_path / "artifacts"
    (artifacts / "results").mkdir(parents=True)
    (artifacts / "demo_dbs").mkdir()
    (artifacts / "results" / "router_config.json").write_text(
        json.dumps({
            "threshold": 0.5,
            "costs": {
                "c_prefill": 0.0,
                "c_decode": 0.0,
                "c_api": 0.001,
                "api_in_per_tok": 0.0,
                "api_out_per_tok": 0.0,
            },
        })
    )
    (artifacts / "demo_dbs" / "index.json").write_text("[]")
    monkeypatch.setattr(main.settings, "artifacts", artifacts)
    monkeypatch.setattr(main.settings, "mode", "replay")

    with TestClient(main.app) as client:
        response = client.post(
            "/api/auth/register",
            json={"email": "upload@example.com", "password": "correct horse battery"},
        )
        assert response.status_code == 201, response.text
        client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        yield client, artifacts


def test_upload_multiple_csvs_registers_typed_tables(upload_client):
    client, artifacts = upload_client

    response = client.post(
        "/api/upload-database",
        data={"db_id": "retail_data"},
        files=[
            ("files", ("customers.csv", b"id,full name\n1,Ada\n2,Grace\n", "text/csv")),
            ("files", ("orders.csv", b"order_id,total\n10,12.50\n11,7.00\n", "text/csv")),
        ],
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["table_names"] == ["customers", "orders"]
    assert result["row_counts"] == {"customers": 2, "orders": 2}
    assert client.get("/api/databases").json()[-1]["db_id"] == "retail_data"
    assert json.loads((artifacts / "demo_dbs" / "index.json").read_text()) == ["retail_data"]

    with sqlite3.connect(artifacts / "demo_dbs" / "retail_data" / "retail_data.sqlite") as connection:
        columns = connection.execute('PRAGMA table_info("orders")').fetchall()
        assert [(column[1], column[2]) for column in columns] == [
            ("order_id", "INTEGER"),
            ("total", "REAL"),
        ]
        assert connection.execute('SELECT COUNT(*) FROM "customers"').fetchone()[0] == 2


def test_upload_zip_of_csvs_creates_tables(upload_client):
    client, _ = upload_client
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("tables/teams.csv", "team_id,name\n1,Comets\n")
        zipped.writestr("tables/players.csv", "player_id,team_id\n8,1\n")

    response = client.post(
        "/api/upload-database",
        data={"db_id": "league"},
        files={"file": ("league.zip", archive.getvalue(), "application/zip")},
    )

    assert response.status_code == 200, response.text
    assert response.json()["table_names"] == ["teams", "players"]


def test_malformed_csv_is_rejected_without_registering_database(upload_client):
    client, artifacts = upload_client

    response = client.post(
        "/api/upload-database",
        files={"file": ("bad_rows.csv", b"id,name\n1,Ada\n2\n", "text/csv")},
    )

    assert response.status_code == 400
    assert "row 3" in response.json()["detail"]
    assert json.loads((artifacts / "demo_dbs" / "index.json").read_text()) == []


def test_deleting_uploaded_database_removes_it_from_index(upload_client):
    client, artifacts = upload_client
    uploaded = client.post(
        "/api/upload-database",
        files={"file": ("temporary.csv", b"id,value\n1,ok\n", "text/csv")},
    )
    assert uploaded.status_code == 200, uploaded.text

    response = client.delete("/api/database/temporary")

    assert response.status_code == 200
    assert json.loads((artifacts / "demo_dbs" / "index.json").read_text()) == []
    assert "temporary" not in [item["db_id"] for item in client.get("/api/databases").json()]


def test_custom_question_without_teacher_api_returns_actionable_error(upload_client):
    client, _ = upload_client
    uploaded = client.post(
        "/api/upload-database",
        files={"file": ("products.csv", b"id,name\n1,Desk\n", "text/csv")},
    )
    assert uploaded.status_code == 200, uploaded.text

    from sqlrouter.serve import main

    main.state["teacher"] = None
    response = client.post(
        "/api/route",
        json={"db_id": "products", "question": "List all products", "mode": "auto"},
    )

    assert response.status_code == 503
    assert "configure GROQ_API_KEY" in response.json()["detail"]


def test_uploaded_dataset_profile_reports_nulls_ranges_and_examples(upload_client):
    client, _ = upload_client
    uploaded = client.post(
        "/api/upload-database",
        files={"file": ("measurements.csv", b"site,value\nNorth,1.5\nSouth,\nEast,3.0\n", "text/csv")},
    )
    assert uploaded.status_code == 200, uploaded.text

    response = client.get("/api/database/measurements/profile")

    assert response.status_code == 200
    table = response.json()["tables"][0]
    assert table["name"] == "measurements"
    assert table["row_count"] == 3
    value_column = next(column for column in table["columns"] if column["name"] == "value")
    assert value_column["type"] == "REAL"
    assert value_column["null_count"] == 1
    assert value_column["min"] == 1.5
    assert value_column["max"] == 3.0
    assert table["examples"][0] == {"site": "North", "value": 1.5}


def test_route_preview_waits_for_confirmation_and_execution_is_read_only(upload_client):
    client, artifacts = upload_client
    uploaded = client.post(
        "/api/upload-database",
        files={"file": ("items.csv", b"id,name\n1,Desk\n2,Chair\n", "text/csv")},
    )
    assert uploaded.status_code == 200, uploaded.text

    from sqlrouter.serve import main

    class SqlTeacher:
        provider = "test"
        model = "fixed"

        def sql(self, messages):
            if "delete" in str(messages).lower():
                return "DELETE FROM items", 10, 5
            return "SELECT COUNT(*) FROM items", 10, 5

    main.state["teacher"] = SqlTeacher()
    preview = client.post(
        "/api/route",
        json={
            "db_id": "items",
            "question": "How many items are there?",
            "mode": "auto",
            "preview_only": True,
        },
    )

    assert preview.status_code == 200, preview.text
    data = preview.json()
    assert data["requires_confirmation"] is True
    assert data["rows"] == []
    assert data["query_id"]

    changed_after_review = client.post(
        "/api/execute-preview",
        json={
            "query_id": data["query_id"],
            "db_id": "items",
            "question": "How many items are there?",
            "sql": "DELETE FROM items",
            "route": data["route"],
        },
    )
    assert changed_after_review.status_code == 409

    executed = client.post(
        "/api/execute-preview",
        json={
            "query_id": data["query_id"],
            "db_id": "items",
            "question": "How many items are there?",
            "sql": data["sql"],
            "route": data["route"],
        },
    )
    assert executed.status_code == 200, executed.text
    assert executed.json()["rows"] == [[2]]

    feedback = client.post(
        "/api/feedback",
        json={
            "query_id": data["query_id"],
            "correct": False,
            "expected_answer": "There are two items.",
        },
    )
    assert feedback.status_code == 200, feedback.text
    saved_feedback = json.loads((artifacts / "results" / "user_feedback.json").read_text())
    assert saved_feedback == [{
        "query_id": data["query_id"],
        "timestamp": saved_feedback[0]["timestamp"],
        "db_id": "items",
        "question": "How many items are there?",
        "sql": data["sql"],
        "route": data["route"],
        "correct": False,
        "expected_answer": "There are two items.",
    }]

    write_preview = client.post(
        "/api/route",
        json={
            "db_id": "items",
            "question": "Delete an item",
            "mode": "auto",
            "preview_only": True,
        },
    )
    assert write_preview.status_code == 200
    write_data = write_preview.json()
    write_attempt = client.post(
        "/api/execute-preview",
        json={
            "query_id": write_data["query_id"],
            "db_id": "items",
            "question": "Delete an item",
            "sql": write_data["sql"],
            "route": write_data["route"],
        },
    )
    assert write_attempt.status_code == 200, write_attempt.text
    assert write_attempt.json()["status"] == "err"


def test_retired_teacher_model_returns_actionable_error(upload_client):
    client, _ = upload_client
    uploaded = client.post(
        "/api/upload-database",
        files={"file": ("flights.csv", b"flight_id\n1\n", "text/csv")},
    )
    assert uploaded.status_code == 200, uploaded.text

    from sqlrouter.serve import main

    class RetiredModelTeacher:
        provider = "groq"
        model = "retired-model"

        def sql(self, _messages):
            error = RuntimeError("model_not_found")
            error.status_code = 404
            raise error

    main.state["teacher"] = RetiredModelTeacher()
    response = client.post(
        "/api/route",
        json={"db_id": "flights", "question": "Show number of flights", "mode": "auto"},
    )

    assert response.status_code == 503
    assert "configured groq model 'retired-model' is unavailable" in response.json()["detail"]
    assert "restart the backend" in response.json()["detail"]


def test_follow_up_question_includes_recent_context(upload_client):
    client, _ = upload_client
    uploaded = client.post(
        "/api/upload-database",
        files={"file": ("items.csv", b"id,name\n1,Desk\n2,Chair\n", "text/csv")},
    )
    assert uploaded.status_code == 200, uploaded.text

    from sqlrouter.serve import main

    class ContextTeacher:
        provider = "test"
        model = "fixed"

        def sql(self, messages):
            self.messages = messages
            return "SELECT COUNT(*) FROM items", 10, 5

    teacher = ContextTeacher()
    main.state["teacher"] = teacher
    response = client.post(
        "/api/route",
        json={
            "db_id": "items",
            "question": "And how many are there?",
            "preview_only": True,
            "context": [
                {
                    "question": "List the items",
                    "sql": "SELECT name FROM items",
                }
            ],
        },
    )

    assert response.status_code == 200, response.text
    user_prompt = teacher.messages[1]["content"]
    assert "Previous question: List the items" in user_prompt
    assert "Previous SQL: SELECT name FROM items" in user_prompt
    assert "Current question: And how many are there?" in user_prompt
