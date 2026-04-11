from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.models import SearchRequest
from app.providers.flight_provider import FlightProvider, FlightProviderError


class DuffelFlightProvider(FlightProvider):
    provider_name = "duffel_test"

    def __init__(
        self,
        access_token: str,
        *,
        base_url: str = "https://api.duffel.com",
        version: str = "v2",
        timeout_seconds: float = 20.0,
    ) -> None:
        if not access_token:
            raise FlightProviderError(
                "Duffel access token is missing. Set DUFFEL_ACCESS_TOKEN."
            )

        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_seconds)
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Duffel-Version": version,
        }

    def search_one_way(
        self,
        request: SearchRequest,
        origin_airport: str,
        destination_airport: str,
    ) -> list[dict]:
        max_connections = request.max_stops if request.max_stops is not None else 1
        payload = {
            "data": {
                "slices": [
                    {
                        "origin": origin_airport,
                        "destination": destination_airport,
                        "departure_date": request.departure_date.isoformat(),
                    }
                ],
                "passengers": [{"type": "adult"}],
                "cabin_class": request.cabin_class,
                "max_connections": max_connections,
            }
        }

        try:
            response = self._client.post(
                "/air/offer_requests",
                headers=self._headers,
                params={"return_offers": "true", "supplier_timeout": 10000},
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise FlightProviderError(f"Duffel flight search failed: {exc}") from exc

        if response.status_code >= 400:
            raise FlightProviderError(self._format_http_error("Duffel flight search", response))

        data = response.json().get("data", {})
        offers = data.get("offers") or []
        mapped_offers: list[dict] = []
        for raw_offer in offers:
            mapped_offer = self._map_offer(raw_offer, self.provider_name)
            if mapped_offer is not None:
                mapped_offers.append(mapped_offer)
        return mapped_offers

    @classmethod
    def _map_offer(cls, raw_offer: dict[str, Any], provider_name: str) -> dict[str, Any] | None:
        slices = raw_offer.get("slices") or []
        if not slices:
            return None

        journey_slice = slices[0]
        segments = journey_slice.get("segments") or []
        if not segments:
            return None

        first_segment = segments[0]
        last_segment = segments[-1]
        operating_carrier = (
            first_segment.get("operating_carrier")
            or first_segment.get("marketing_carrier")
            or {}
        )
        total_amount = raw_offer.get("total_amount") or raw_offer.get("base_amount") or "0"
        total_currency = raw_offer.get("total_currency") or raw_offer.get("base_currency") or "USD"

        return {
            "provider": provider_name,
            "airline": operating_carrier.get("name", "Unknown Airline"),
            "origin_airport": first_segment.get("origin", {}).get("iata_code", ""),
            "destination_airport": last_segment.get("destination", {}).get("iata_code", ""),
            "original_price": float(total_amount),
            "original_currency": str(total_currency).upper(),
            "purchase_link": None,
            "departure_time": cls._extract_hhmm(first_segment.get("departing_at")),
            "arrival_time": cls._extract_hhmm(last_segment.get("arriving_at")),
            "duration_minutes": cls._sum_segment_minutes(segments),
            "stops": max(len(segments) - 1, 0),
        }

    @staticmethod
    def _extract_hhmm(value: str | None) -> str:
        if not value:
            return "00:00"
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%H:%M")
        except ValueError:
            return value[11:16] if len(value) >= 16 else "00:00"

    @classmethod
    def _sum_segment_minutes(cls, segments: list[dict[str, Any]]) -> int:
        total = 0
        for segment in segments:
            departing_at = segment.get("departing_at")
            arriving_at = segment.get("arriving_at")
            if not departing_at or not arriving_at:
                continue
            try:
                depart = datetime.fromisoformat(departing_at.replace("Z", "+00:00"))
                arrive = datetime.fromisoformat(arriving_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            total += max(int((arrive - depart).total_seconds() // 60), 0)
        return total

    @staticmethod
    def _format_http_error(prefix: str, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        return f"{prefix} failed with status {response.status_code}: {payload}"
