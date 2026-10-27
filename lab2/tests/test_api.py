import pytest
from fastapi.testclient import TestClient

import agro_api.main as service

PAYLOAD = {
    "farm_id": "FARM-001",
    "region": "Krasnodar",
    "crop_type": "wheat",
    "area_ha": 2500,
    "temperature_avg": 24.3,
    "precipitation_mm": 320,
    "payment_delay_days": 45,
    "previous_defaults": 1,
    "debt": 6_500_000,
}


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Каждый тест использует отдельную SQLite-базу и не зависит от локальных данных.
    monkeypatch.setattr(service, "DATABASE_PATH", tmp_path / "test_agro_scoring.db")
    with TestClient(service.app) as test_client:
        yield test_client


def test_health_and_request_headers(client):
    response = client.get("/health", headers={"X-Request-ID": "test-request-123"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "test-request-123"
    assert float(response.headers["X-Process-Time"]) >= 0


def test_model_info(client):
    response = client.get("/model-info")
    assert response.status_code == 200
    assert response.json()["model_name"] == "agro-risk-model"


def test_predict_saves_and_gets_prediction(client):
    response = client.post("/predict", json=PAYLOAD, headers={"X-Request-ID": "predict-001"})
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "predict-001"
    assert data["risk_score"] == 0.9
    assert data["risk_level"] == "high"

    stored = client.get(f"/predictions/{data['request_id']}")
    assert stored.status_code == 200
    assert stored.json() == data

    history = client.get("/predictions")
    assert history.status_code == 200
    assert any(row["request_id"] == "predict-001" for row in history.json())


def test_pydantic_and_business_validation(client):
    assert client.post("/predict", json={**PAYLOAD, "area_ha": -100}).status_code == 422
    assert client.post("/predict", json={**PAYLOAD, "region": "Moscow"}).status_code == 400


def test_not_found_and_error_request_id(client):
    response = client.get("/predictions/does-not-exist", headers={"X-Request-ID": "missing-001"})
    assert response.status_code == 404
    assert response.json()["request_id"] == "missing-001"


def test_query_validation_and_filtering(client):
    assert client.get("/predictions?limit=-5").status_code == 422
    client.post("/predict", json=PAYLOAD)
    assert client.get("/predictions?limit=2").status_code == 200
    assert client.get("/predictions?risk_level=high").status_code == 200
    assert client.get("/predictions?risk_level=unknown").status_code == 400


def test_explicit_batch_and_ambiguous_request_id(client):
    response = client.post(
        "/batch-predict",
        json={"items": [PAYLOAD, {**PAYLOAD, "farm_id": "FARM-002"}]},
        headers={"X-Request-ID": "batch-001"},
    )
    assert response.status_code == 200
    assert response.json()["batch_size"] == 2

    assert client.get("/predictions/batch-001").status_code == 409
    all_items = client.get("/requests/batch-001/predictions")
    assert all_items.status_code == 200
    assert len(all_items.json()) == 2


def test_batch_size_validation(client):
    response = client.post("/batch-predict", json={"items": [PAYLOAD] * (service.MAX_BATCH_SIZE + 1)})
    assert response.status_code == 422


def test_queued_inference_and_queue_status(client):
    response = client.post("/predict-queued", json=PAYLOAD, headers={"X-Request-ID": "queued-001"})
    assert response.status_code == 200
    assert response.json()["request_id"] == "queued-001"

    status_response = client.get("/queue-status")
    assert status_response.status_code == 200
    assert status_response.json()["queue_max_size"] == service.QUEUE_MAX_SIZE
    assert status_response.json()["max_batch_size"] == service.MAX_BATCH_SIZE


def test_weekday_pagination_validation(client):
    assert client.get("/predictions/by-weekday?weekday=monday&page=-1&per_page=5").status_code == 422
    assert client.get("/predictions/by-weekday?weekday=funday&page=1&per_page=5").status_code == 400
    assert client.get("/predictions/by-weekday?weekday=monday&page=1&per_page=5").status_code == 200


def test_llm_endpoints_with_mocked_provider(client, monkeypatch):
    async def fake_llm_call(client, prompt, request_id, model="auto", temperature=0.3, max_tokens=300):
        return {
            "request_id": request_id,
            "requested_model": model,
            "returned_model": "mock-model",
            "answer": "Учебное объяснение",
            "reasoning": None,
            "finish_reason": "stop",
            "usage": None,
            "latency_ms": 1.0,
        }

    monkeypatch.setattr(service, "call_vireonix_llm", fake_llm_call)
    chat = client.post("/llm/chat", json={"prompt": "Объясни агроскоринг"})
    assert chat.status_code == 200
    assert chat.json()["answer"] == "Учебное объяснение"

    combined = client.post("/predict-with-llm", json=PAYLOAD)
    assert combined.status_code == 200
    assert combined.json()["prediction"]["risk_score"] == 0.9
    assert combined.json()["llm"]["answer"] == "Учебное объяснение"
