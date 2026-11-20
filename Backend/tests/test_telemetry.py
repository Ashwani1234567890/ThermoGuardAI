from fastapi.testclient import TestClient


def create_16_readings(base_temp: float = 27.0):
    return [
        {
            "sensor_id": i,
            "temperature": round(base_temp + (i * 0.1), 2),
            "raw_adc_value": int(base_temp * 30),
            "sensor_status": "valid"
        }
        for i in range(16)
    ]


def test_ingest_valid_telemetry(client: TestClient):
    payload = {
        "device_id": "ESP32-TELEMETRY-01",
        "readings": create_16_readings(26.5),
        "sequence_number": 1,
        "boot_count": 0,
        "uptime_ms": 5000,
        "deterministic_safety_state": "NORMAL",
        "ai_prediction": {
            "class_index": 2,
            "class_name": "normal",
            "confidence": 0.95
        }
    }
    response = client.post("/api/telemetry", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["device_id"] == "ESP32-TELEMETRY-01"
    assert data["readings_saved"] == 16
    assert "summary" in data
    assert data["summary"]["max_temperature"] > data["summary"]["min_temperature"]


def test_reject_incomplete_sensor_count(client: TestClient):
    # Only 15 sensors provided
    readings = create_16_readings(25.0)[:15]
    payload = {
        "device_id": "ESP32-TELEMETRY-01",
        "readings": readings,
        "deterministic_safety_state": "NORMAL"
    }
    response = client.post("/api/telemetry", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_reject_duplicate_sensor_ids(client: TestClient):
    readings = create_16_readings(25.0)
    readings[1]["sensor_id"] = 0  # Duplicate sensor_id 0
    payload = {
        "device_id": "ESP32-TELEMETRY-01",
        "readings": readings,
        "deterministic_safety_state": "NORMAL"
    }
    response = client.post("/api/telemetry", json=payload)
    assert response.status_code == 422


def test_latest_grid_telemetry(client: TestClient):
    device_id = "ESP32-GRID-01"
    payload = {
        "device_id": device_id,
        "readings": create_16_readings(30.0),
        "sequence_number": 42,
        "deterministic_safety_state": "NORMAL"
    }
    client.post("/api/telemetry", json=payload)

    response = client.get(f"/api/telemetry/latest/{device_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == device_id
    assert len(data["grid_4x4"]) == 4
    for row in data["grid_4x4"]:
        assert len(row) == 4
    assert data["is_online"] is True


def test_telemetry_batch_ingestion(client: TestClient):
    device_id = "ESP32-BATCH-01"
    batch_payload = {
        "batches": [
            {
                "device_id": device_id,
                "readings": create_16_readings(25.0),
                "sequence_number": 1,
                "deterministic_safety_state": "NORMAL"
            },
            {
                "device_id": device_id,
                "readings": create_16_readings(26.0),
                "sequence_number": 2,
                "deterministic_safety_state": "NORMAL"
            }
        ]
    }
    response = client.post("/api/telemetry/batch", json=batch_payload)
    assert response.status_code == 201
    assert len(response.json()) == 2


def test_historical_telemetry_query(client: TestClient):
    device_id = "ESP32-HIST-01"
    payload = {
        "device_id": device_id,
        "readings": create_16_readings(28.0),
        "deterministic_safety_state": "NORMAL"
    }
    client.post("/api/telemetry", json=payload)

    # Query all sensors history
    res_all = client.get(f"/api/telemetry/history/{device_id}?page=1&page_size=50")
    assert res_all.status_code == 200
    assert res_all.json()["total_records"] == 16

    # Query sensor 5 only
    res_s5 = client.get(f"/api/telemetry/history/{device_id}?sensor_id=5")
    assert res_s5.status_code == 200
    assert res_s5.json()["total_records"] == 1
    assert res_s5.json()["readings"][0]["sensor_id"] == 5
