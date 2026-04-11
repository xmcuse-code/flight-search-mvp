from __future__ import annotations

from app.providers.amadeus_provider import AmadeusFlightProvider
from app.providers.duffel_provider import DuffelFlightProvider
from app.providers.flight_provider import FlightProvider, FlightProviderError
from app.providers.mock_provider import MockFlightProvider
from app.settings import Settings


class FallbackFlightProvider(FlightProvider):
    provider_name = "fallback_provider"

    def __init__(self, primary: FlightProvider, fallback: FlightProvider) -> None:
        self._primary = primary
        self._fallback = fallback
        self.provider_name = primary.provider_name

    def search_one_way(self, request, origin_airport: str, destination_airport: str) -> list[dict]:
        try:
            return self._primary.search_one_way(request, origin_airport, destination_airport)
        except FlightProviderError:
            return self._fallback.search_one_way(request, origin_airport, destination_airport)


def create_flight_provider(settings: Settings) -> FlightProvider:
    if settings.flight_provider == "mock":
        return MockFlightProvider()

    if settings.flight_provider == "duffel":
        if not settings.duffel_access_token:
            raise ValueError(
                "FLIGHT_PROVIDER=duffel requires DUFFEL_ACCESS_TOKEN to be set."
            )
        return DuffelFlightProvider(
            access_token=settings.duffel_access_token,
            base_url=settings.duffel_base_url,
            version=settings.duffel_version,
            timeout_seconds=settings.duffel_timeout_seconds,
        )

    if settings.flight_provider == "auto":
        if settings.duffel_access_token:
            return FallbackFlightProvider(
                primary=DuffelFlightProvider(
                    access_token=settings.duffel_access_token,
                    base_url=settings.duffel_base_url,
                    version=settings.duffel_version,
                    timeout_seconds=settings.duffel_timeout_seconds,
                ),
                fallback=MockFlightProvider(),
            )
        if settings.amadeus_client_id and settings.amadeus_client_secret:
            return FallbackFlightProvider(
                primary=AmadeusFlightProvider(
                    client_id=settings.amadeus_client_id,
                    client_secret=settings.amadeus_client_secret,
                    base_url=settings.amadeus_base_url,
                    timeout_seconds=settings.amadeus_timeout_seconds,
                ),
                fallback=MockFlightProvider(),
            )
        return MockFlightProvider()

    if not settings.amadeus_client_id or not settings.amadeus_client_secret:
        raise ValueError(
            "FLIGHT_PROVIDER=amadeus requires AMADEUS_CLIENT_ID and "
            "AMADEUS_CLIENT_SECRET to be set."
        )

    return AmadeusFlightProvider(
        client_id=settings.amadeus_client_id,
        client_secret=settings.amadeus_client_secret,
        base_url=settings.amadeus_base_url,
        timeout_seconds=settings.amadeus_timeout_seconds,
    )
