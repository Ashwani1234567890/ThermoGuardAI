from fastapi.testclient import TestClient


def test_create_and_fetch_event(client: TestClient):
    # Register device
    client.post("/api/devices/register", json={"device_id": "ESP32-EV-01", "device_name": "Event Device"})

    event_payload = {
        "device_id": "ESP32-EV-01",
        "event_type": "hotspot",
        "severity": "WARNING",
        "affected_sensor": 4,
        "temperature": 52.4,
        "temperature_rise_rate": 1.5,
        "confidence": 0.89,
        "ai_class": "hotspot",
        "description": "Localized hotspot detected around sensor 4"
    }
    create_res = client.post("/api/events", json=event_payload)
    assert create_res.status_code == 201
    event_data = create_res.json()
    assert event_data["id"] is not None
    assert event_data["severity"] == "WARNING"
    assert event_data["acknowledged"] is False

    # Fetch event by ID
    event_id = event_data["id"]
    get_res = client.get(f"/api/events/{event_id}")
    assert get_res.status_code == 200
    assert get_res.json()["affected_sensor"] == 4


def test_acknowledge_event(client: TestClient):
    client.post("/api/devices/register", json={"device_id": "ESP32-EV-02", "device_name": "Ack Device"})
    event_payload = {
        "device_id": "ESP32-EV-02",
        "event_type": "rapid_rise",
        "severity": "CRITICAL",
        "temperature": 78.5,
        "description": "Rapid thermal rise triggering critical shutdown"
    }
    create_res = client.post("/api/events", json=event_payload)
    event_id = create_res.json()["id"]

    # Acknowledge event
    ack_res = client.patch(
        f"/api/events/{event_id}/acknowledge",
        json={"acknowledged_by": "SeniorSafetyEngineer"}
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["acknowledged"] is True
    assert ack_res.json()["acknowledged_by"] == "SeniorSafetyEngineer"
    assert ack_res.json()["acknowledged_at"] is not None


def test_filter_events(client: TestClient):
    client.post("/api/devices/register", json={"device_id": "ESP32-EV-FILTER", "device_name": "Filter Dev"})

    # Create one warning, one critical
    client.post("/api/events", json={
        "device_id": "ESP32-EV-FILTER",
        "event_type": "hotspot",
        "severity": "WARNING",
        "temperature": 51.0,
        "description": "Warning 1"
    })
    client.post("/api/events", json={
        "device_id": "ESP32-EV-FILTER",
        "event_type": "rapid_rise",
        "severity": "CRITICAL",
        "temperature": 80.0,
        "description": "Critical 1"
    })

    # Filter by severity CRITICAL
    res_crit = client.get("/api/events?severity=CRITICAL")
    assert res_crit.status_code == 200
    assert len(res_crit.json()) == 1
    assert res_crit.json()[0]["severity"] == "CRITICAL"

    # Filter by device_id
    res_dev = client.get("/api/events?device_id=ESP32-EV-FILTER")
    assert res_dev.status_code == 200
    assert len(res_dev.json()) == 2
