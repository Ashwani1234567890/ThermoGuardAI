from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    Default values provide out-of-the-box local development compatibility.
    """
    APP_NAME: str = "ThermoGuardAI Backend"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str = "sqlite:///./database/thermal_monitoring.db"

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # ESP32 Communication Configuration
    UDP_ENABLED: bool = True
    UDP_HOST: str = "0.0.0.0"
    UDP_PORT: int = 5005
    DEVICE_OFFLINE_THRESHOLD_SECONDS: int = 30

    # Deterministic Safety Defaults
    MAX_ALLOWABLE_TEMPERATURE_C: float = 75.0
    WARNING_TEMPERATURE_C: float = 50.0
    MAX_RATE_OF_CHANGE_C_PER_SEC: float = 2.0
    MAX_SPATIAL_RANGE_C: float = 15.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
