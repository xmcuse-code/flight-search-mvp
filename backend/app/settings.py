from __future__ import annotations

import os
from dataclasses import dataclass


def _parse_csv_env(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    environment: str
    host: str
    port: int
    cors_allow_origins: list[str]
    flight_provider: str
    amadeus_client_id: str | None
    amadeus_client_secret: str | None
    amadeus_base_url: str
    amadeus_timeout_seconds: float


def get_settings() -> Settings:
    environment = os.getenv("APP_ENV", "development").strip().lower()
    host = os.getenv("BACKEND_HOST", "0.0.0.0").strip()
    port = int(os.getenv("PORT") or os.getenv("BACKEND_PORT") or "8000")
    cors_allow_origins = _parse_csv_env(os.getenv("CORS_ALLOW_ORIGINS"))
    flight_provider = os.getenv("FLIGHT_PROVIDER", "mock").strip().lower()
    amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID")
    amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    amadeus_base_url = os.getenv(
        "AMADEUS_BASE_URL",
        "https://test.api.amadeus.com",
    ).rstrip("/")
    amadeus_timeout_seconds = float(os.getenv("AMADEUS_TIMEOUT_SECONDS", "15"))

    if flight_provider not in {"mock", "amadeus", "auto"}:
        raise ValueError(
            "FLIGHT_PROVIDER must be one of: mock, amadeus, auto"
        )

    if not cors_allow_origins:
        if environment == "production":
            cors_allow_origins = ["https://example.com"]
        else:
            cors_allow_origins = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
            ]

    return Settings(
        environment=environment,
        host=host,
        port=port,
        cors_allow_origins=cors_allow_origins,
        flight_provider=flight_provider,
        amadeus_client_id=amadeus_client_id.strip() if amadeus_client_id else None,
        amadeus_client_secret=(
            amadeus_client_secret.strip() if amadeus_client_secret else None
        ),
        amadeus_base_url=amadeus_base_url,
        amadeus_timeout_seconds=amadeus_timeout_seconds,
    )
