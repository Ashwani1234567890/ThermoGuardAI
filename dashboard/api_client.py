"""
Dedicated Backend API Client for SHADOW THERMOGUARD AI Frontend.
Communicates strictly via REST HTTP interfaces exposed by the existing FastAPI backend.
Handles errors, connection drops, parsing, timeouts, and structure validation gracefully.
DOES NOT MODIFY ANY BACKEND CODE OR ASSUME UNDECLARED ENDPOINTS.
"""

import requests
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger("thermoguard.frontend.api")


class BackendAPIClient:
    """Client for consuming existing ThermoGuardAI FastAPI REST endpoints."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 3.5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def update_base_url(self, new_url: str):
        """Updates the target backend base URL dynamically from UI input."""
        self.base_url = new_url.rstrip("/")

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[Any], Optional[str]]:
        """
        Generic HTTP request wrapper with robust error, timeout, and exception handling.
        Returns (success: bool, data: Optional[Any], error_message: Optional[str]).
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout
            )
            if response.status_code in (200, 201):
                try:
                    return True, response.json(), None
                except Exception:
                    return True, response.text, None
            elif response.status_code == 404:
                return False, None, "Resource not found (404)"
            elif response.status_code == 422:
                return False, None, f"Payload validation error (422): {response.text}"
            else:
                return False, None, f"HTTP Error {response.status_code}: {response.text}"

        except requests.exceptions.ConnectionError:
            return False, None, f"Connection refused to {self.base_url}. Is FastAPI running?"
        except requests.exceptions.Timeout:
            return False, None, f"Request timed out after {self.timeout}s to {url}"
        except Exception as e:
            return False, None, f"Unexpected request failure: {str(e)}"

    # -------------------------------------------------------------
    # 1. Health Endpoints
    # -------------------------------------------------------------
    def get_root(self) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Calls existing GET /"""
        return self._request("GET", "/")

    def get_health(self) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Calls existing GET /api/health"""
        return self._request("GET", "/api/health")

    # -------------------------------------------------------------
    # 2. Devices Endpoints
    # -------------------------------------------------------------
    def get_devices(self) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """Calls existing GET /api/devices"""
        return self._request("GET", "/api/devices")

    def get_device(self, device_id: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Calls existing GET /api/devices/{device_id}"""
        return self._request("GET", f"/api/devices/{device_id}")

    def get_device_status(self, device_id: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Calls existing GET /api/devices/{device_id}/status"""
        return self._request("GET", f"/api/devices/{device_id}/status")

    def register_device(
        self,
        device_id: str,
        device_name: str,
        firmware_version: str = "1.0.0",
        ip_address: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Calls existing POST /api/devices/register"""
        payload = {
            "device_id": device_id,
            "device_name": device_name,
            "firmware_version": firmware_version,
            "ip_address": ip_address
        }
        return self._request("POST", "/api/devices/register", json_data=payload)

    # -------------------------------------------------------------
    # 3. Telemetry Endpoints
    # -------------------------------------------------------------
    def get_latest_telemetry(self, device_id: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Calls existing GET /api/telemetry/latest/{device_id}
        Returns 4x4 grid matrix, summary metrics, safety state, and AI classification.
        """
        return self._request("GET", f"/api/telemetry/latest/{device_id}")

    def get_telemetry_history(
        self,
        device_id: str,
        sensor_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 100
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Calls existing GET /api/telemetry/history/{device_id}"""
        params = {"page": page, "page_size": page_size}
        if sensor_id is not None:
            params["sensor_id"] = sensor_id
        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()

        return self._request("GET", f"/api/telemetry/history/{device_id}", params=params)

    # -------------------------------------------------------------
    # 4. Thermal Events Endpoints
    # -------------------------------------------------------------
    def get_events(
        self,
        device_id: Optional[str] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """Calls existing GET /api/events with optional filters"""
        params = {"page": page, "page_size": page_size}
        if device_id:
            params["device_id"] = device_id
        if event_type:
            params["event_type"] = event_type
        if severity:
            params["severity"] = severity
        if acknowledged is not None:
            params["acknowledged"] = acknowledged
        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()

        return self._request("GET", "/api/events", params=params)

    def get_event(self, event_id: int) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Calls existing GET /api/events/{event_id}"""
        return self._request("GET", f"/api/events/{event_id}")

    def acknowledge_event(
        self,
        event_id: int,
        acknowledged_by: str = "Operator"
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Calls existing PATCH /api/events/{event_id}/acknowledge"""
        payload = {"acknowledged_by": acknowledged_by}
        return self._request("PATCH", f"/api/events/{event_id}/acknowledge", json_data=payload)
