from fastapi.testclient import TestClient

from agro_api.main import app

client = TestClient(app)

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


def test_health():
    assert client.get("/health").status_code == 200


def test_model_info():
    response = client.get("/model-info")
    assert response.status_code == 200
    assert response.json()["model_name"] == "agro-risk-model"


def test_predict_and_get_prediction():
    response = client.post("/predict", json=PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] == 0.9
    assert data["risk_level"] == "high"

    stored = client.get(f"/predictions/{data['request_id']}")
    assert stored.status_code == 200
    assert stored.json() == data


def test_pydantic_validation():
    bad = {**PAYLOAD, "area_ha": -100}
    assert client.post("/predict", json=bad).status_code == 422


def test_unknown_region():
    bad = {**PAYLOAD, "region": "Moscow"}
    assert client.post("/predict", json=bad).status_code == 400


def test_not_found():
    assert client.get("/predictions/does-not-exist").status_code == 404


def test_query_validation_and_filtering():
    assert client.get("/predictions?limit=-5").status_code == 422
    client.post("/predict", json=PAYLOAD)
    assert client.get("/predictions?limit=2").status_code == 200
    assert client.get("/predictions?risk_level=high").status_code == 200
    assert client.get("/predictions?risk_level=unknown").status_code == 400
