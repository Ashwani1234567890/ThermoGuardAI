from fastapi.testclient import TestClient


def test_register_device(client: TestClient):
    payload = {
        "device_id": "ESP32-TEST-001",
        "device_name": "Grid Unit Alpha",
        "firmware_version": "1.2.0",
        "ip_address": "192.168.1.50"
    }
    response = client.post("/api/devices/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["device_id"] == "ESP32-TEST-001"
    assert data["device_name"] == "Grid Unit Alpha"
    assert data["status"] == "online"


def test_get_device_by_id(client: TestClient):
    # Register device
    reg_payload = {
        "device_id": "ESP32-TEST-002",
        "device_name": "Grid Unit Beta",
        "firmware_version": "1.0.0"
    }
    client.post("/api/devices/register", json=reg_payload)

    # Fetch device
    response = client.get("/api/devices/ESP32-TEST-002")
    assert response.status_code == 200
    assert response.json()["device_id"] == "ESP32-TEST-002"

    # Non-existent device
    not_found = client.get("/api/devices/NON-EXISTENT")
    assert not_found.status_code == 404


def test_list_devices(client: TestClient):
    client.post("/api/devices/register", json={"device_id": "DEV-1", "device_name": "Unit 1"})
    client.post("/api/devices/register", json={"device_id": "DEV-2", "device_name": "Unit 2"})

    response = client.get("/api/devices")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_device_status_online(client: TestClient):
    client.post("/api/devices/register", json={"device_id": "DEV-LIVE", "device_name": "Live Unit"})
    response = client.get("/api/devices/DEV-LIVE/status")
    assert response.status_code == 200
    data = response.json()
    assert data["is_online"] is True
    assert data["seconds_since_last_seen"] < 5.0
