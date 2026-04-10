from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import httpx

from app.models import SearchRequest
from app.providers.flight_provider import FlightProvider, FlightProviderError


class AmadeusFlightProvider(FlightProvider):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        base_url: str = "https://test.api.amadeus.com",
        timeout_seconds: float = 15.0,
    ) -> None:
        if not client_id or not client_secret:
            raise FlightProviderError(
                "Amadeus credentials are missing. Set AMADEUS_CLIENT_ID and "
                "AMADEUS_CLIENT_SECRET."
            )

        self.provider_name = (
            "amadeus_live" if "test.api.amadeus.com" not in base_url else "amadeus_test"
        )
        self._client_id = client_id
        self._client_secret = client_secret
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_seconds)
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    def search_one_way(
        self,
        request: SearchRequest,
        origin_airport: str,
        destination_airport: str,
    ) -> list[dict]:
        response = self._request_flight_offers(
            params={
                "originLocationCode": origin_airport,
                "destinationLocationCode": destination_airport,
                "departureDate": request.departure_date.isoformat(),
                "adults": 1,
                "currencyCode": "USD",
                "max": 8,
                "travelClass": (
                    "BUSINESS" if request.cabin_class == "business" else "ECONOMY"
                ),
                "nonStop": "true" if request.max_stops == 0 else "false",
            }
        )
        carrier_lookup = response.get("dictionaries", {}).get("carriers", {})

        offers: list[dict] = []
        for raw_offer in response.get("data", []):
            mapped_offer = self._map_offer(
                raw_offer=raw_offer,
                provider_name=self.provider_name,
                carrier_lookup=carrier_lookup,
            )
            if mapped_offer is not None:
                offers.append(mapped_offer)

        return offers

    def _request_flight_offers(self, params: dict[str, Any]) -> dict[str, Any]:
        access_token = self._get_access_token()
        try:
            response = self._client.get(
                "/v2/shopping/flight-offers",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
        except httpx.HTTPError as exc:
            raise FlightProviderError(f"Amadeus flight search failed: {exc}") from exc
        if response.status_code == 401:
            self._access_token = None
            self._token_expires_at = 0.0
            access_token = self._get_access_token()
            try:
                response = self._client.get(
                    "/v2/shopping/flight-offers",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params,
                )
            except httpx.HTTPError as exc:
                raise FlightProviderError(f"Amadeus flight search failed: {exc}") from exc

        if response.status_code >= 400:
            raise FlightProviderError(self._format_http_error("Amadeus flight search", response))

        return response.json()

    def _get_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        try:
            response = self._client.post(
                "/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.HTTPError as exc:
            raise FlightProviderError(
                f"Amadeus authentication failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise FlightProviderError(self._format_http_error("Amadeus auth", response))

        payload = response.json()
        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 1800))
        if not access_token:
            raise FlightProviderError("Amadeus auth response did not include an access token.")

        self._access_token = access_token
        self._token_expires_at = now + max(expires_in - 60, 60)
        return access_token

    @classmethod
    def _map_offer(
        cls,
        *,
        raw_offer: dict[str, Any],
        provider_name: str,
        carrier_lookup: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        itineraries = raw_offer.get("itineraries") or []
        if not itineraries:
            return None

        itinerary = itineraries[0]
        segments = itinerary.get("segments") or []
        if not segments:
            return None

        first_segment = segments[0]
        last_segment = segments[-1]
        validating_codes = raw_offer.get("validatingAirlineCodes") or []
        airline_code = validating_codes[0] if validating_codes else first_segment.get("carrierCode")
        airline_name = (carrier_lookup or {}).get(airline_code or "", airline_code or "Unknown Airline")
        price = raw_offer.get("price", {})

        return {
            "provider": provider_name,
            "airline": airline_name,
            "origin_airport": first_segment.get("departure", {}).get("iataCode", ""),
            "destination_airport": last_segment.get("arrival", {}).get("iataCode", ""),
            "original_price": float(price.get("grandTotal") or price.get("total") or 0.0),
            "original_currency": str(price.get("currency") or "USD").upper(),
            "purchase_link": None,
            "departure_time": cls._extract_hhmm(first_segment.get("departure", {}).get("at")),
            "arrival_time": cls._extract_hhmm(last_segment.get("arrival", {}).get("at")),
            "duration_minutes": cls._parse_iso8601_duration(
                itinerary.get("duration", "PT0M")
            ),
            "stops": max(len(segments) - 1, 0),
        }

    @staticmethod
    def _extract_hhmm(value: str | None) -> str:
        if not value:
            return "00:00"
        try:
            return datetime.fromisoformat(value).strftime("%H:%M")
        except ValueError:
            return value[11:16] if len(value) >= 16 else "00:00"

    @staticmethod
    def _parse_iso8601_duration(value: str) -> int:
        days = 0
        hours = 0
        minutes = 0
        duration = value.replace("P", "")
        if "D" in duration:
            day_text, duration = duration.split("D", 1)
            days = int(day_text or "0")
        duration = duration.replace("T", "")
        if "H" in duration:
            hour_text, duration = duration.split("H", 1)
            hours = int(hour_text or "0")
        if "M" in duration:
            minute_text = duration.split("M", 1)[0]
            minutes = int(minute_text or "0")
        return (days * 24 * 60) + (hours * 60) + minutes

    @staticmethod
    def _format_http_error(prefix: str, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        return f"{prefix} failed with status {response.status_code}: {payload}"
