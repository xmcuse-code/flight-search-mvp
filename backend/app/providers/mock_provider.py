from __future__ import annotations

import math

from app.config_loader import load_currency_rates, load_mock_flights
from app.models import SearchRequest
from app.providers.flight_provider import FlightProvider
from app.services.airport_catalog_service import AirportCatalogService


class MockFlightProvider(FlightProvider):
    provider_name = "mock_flights"
    _fallback_airlines = [
        "SkyLink Air",
        "Aurora Airways",
        "Global Connect",
        "Pacific Horizon",
        "Northern Wings",
        "MetroJet",
    ]

    def __init__(self) -> None:
        self._data = load_mock_flights()
        self._catalog_service = AirportCatalogService()
        self._rates = load_currency_rates()
        self._supported_currencies = set(self._rates.keys())

    def search_one_way(
        self,
        request: SearchRequest,
        origin_airport: str,
        destination_airport: str,
    ) -> list[dict]:
        offers = self._resolve_route_offers(origin_airport, destination_airport)
        if not offers:
            return []

        results: list[dict] = []
        for index, offer in enumerate(offers):
            cabin_multiplier = 1.0 if request.cabin_class == "economy" else 2.15
            directional_multiplier = 1.0 + (index * 0.025)
            price = round(float(offer["base_price"]) * cabin_multiplier * directional_multiplier, 2)

            results.append(
                {
                    "provider": self.provider_name,
                    "airline": offer["airline"],
                    "origin_airport": origin_airport,
                    "destination_airport": destination_airport,
                    "original_price": price,
                    "original_currency": offer["currency"],
                    "purchase_link": offer.get("purchase_link"),
                    "departure_time": offer["departure_time"],
                    "arrival_time": offer["arrival_time"],
                    "duration_minutes": int(offer["duration_minutes"]),
                    "stops": int(offer["stops"]),
                }
            )

        return results

    def _resolve_route_offers(
        self, origin_airport: str, destination_airport: str
    ) -> list[dict]:
        route_key = f"{origin_airport}-{destination_airport}".upper()
        direct_offers = self._data.get(route_key)
        if direct_offers:
            return direct_offers

        reverse_route_key = f"{destination_airport}-{origin_airport}".upper()
        reverse_offers = self._data.get(reverse_route_key, [])
        if reverse_offers:
            return [
                self._reverse_offer(offer, origin_airport, destination_airport, index)
                for index, offer in enumerate(reverse_offers)
            ]

        return self._generate_synthetic_offers(origin_airport, destination_airport)

    def _reverse_offer(
        self,
        offer: dict,
        origin_airport: str,
        destination_airport: str,
        index: int,
    ) -> dict:
        departure_time = self._shift_time(offer["departure_time"], 9 + index)
        arrival_time = self._shift_time(offer["arrival_time"], 11 + index)
        return {
            "airline": offer["airline"],
            "direct": offer["direct"],
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "stops": int(offer["stops"]),
            "duration_minutes": int(offer["duration_minutes"]) + 10,
            "base_price": round(float(offer["base_price"]) * (1.03 + (index * 0.015)), 2),
            "currency": offer["currency"],
            "purchase_link": self._build_reverse_purchase_link(
                offer.get("purchase_link"),
                origin_airport,
                destination_airport,
            ),
        }

    @staticmethod
    def _build_reverse_purchase_link(
        purchase_link: str | None,
        origin_airport: str,
        destination_airport: str,
    ) -> str | None:
        if not purchase_link:
            return None
        return purchase_link.replace(
            f"/book/{destination_airport}-{origin_airport}",
            f"/book/{origin_airport}-{destination_airport}",
        )

    def _generate_synthetic_offers(
        self,
        origin_airport: str,
        destination_airport: str,
    ) -> list[dict]:
        origin = self._catalog_service.get_airport(origin_airport)
        destination = self._catalog_service.get_airport(destination_airport)
        if not origin or not destination:
            return []

        distance_km = self._haversine_km(
            origin.latitude,
            origin.longitude,
            destination.latitude,
            destination.longitude,
        )
        base_duration = max(75, int((distance_km / 780) * 60))
        source_currency = self._catalog_service.resolve_currency_code(origin_airport) or "USD"
        if source_currency not in self._supported_currencies:
            source_currency = "USD"
        base_price_usd = max(120.0, round(95 + (distance_km * 0.09), 2))
        direct_price = self._to_currency_amount(base_price_usd, source_currency)
        one_stop_price = self._to_currency_amount(base_price_usd * 0.84, source_currency)
        one_stop_alt_price = self._to_currency_amount(base_price_usd * 0.91, source_currency)
        route_seed = sum(ord(char) for char in f"{origin_airport}{destination_airport}")
        direct_available = distance_km < 6800 or route_seed % 3 != 0

        offers: list[dict] = []
        if direct_available:
            offers.append(
                {
                    "airline": self._fallback_airlines[route_seed % len(self._fallback_airlines)],
                    "direct": True,
                    "departure_time": self._seeded_time(route_seed, 6),
                    "arrival_time": self._arrival_time(
                        self._seeded_time(route_seed, 6),
                        base_duration,
                    ),
                    "stops": 0,
                    "duration_minutes": base_duration,
                    "base_price": direct_price,
                    "currency": source_currency,
                    "purchase_link": f"https://example.com/book/{origin_airport}-{destination_airport}-D0",
                }
            )

        stop_duration = base_duration + 115 + (route_seed % 55)
        offers.append(
            {
                "airline": self._fallback_airlines[(route_seed + 1) % len(self._fallback_airlines)],
                "direct": False,
                "departure_time": self._seeded_time(route_seed, 9),
                "arrival_time": self._arrival_time(
                    self._seeded_time(route_seed, 9),
                    stop_duration,
                ),
                "stops": 1,
                "duration_minutes": stop_duration,
                "base_price": one_stop_price,
                "currency": source_currency,
                "purchase_link": f"https://example.com/book/{origin_airport}-{destination_airport}-S1",
            }
        )

        offers.append(
            {
                "airline": self._fallback_airlines[(route_seed + 2) % len(self._fallback_airlines)],
                "direct": False,
                "departure_time": self._seeded_time(route_seed, 14),
                "arrival_time": self._arrival_time(
                    self._seeded_time(route_seed, 14),
                    stop_duration + 40,
                ),
                "stops": 1,
                "duration_minutes": stop_duration + 40,
                "base_price": one_stop_alt_price,
                "currency": source_currency,
                "purchase_link": f"https://example.com/book/{origin_airport}-{destination_airport}-S2",
            }
        )

        return offers

    def _to_currency_amount(self, usd_amount: float, currency: str) -> float:
        return round(usd_amount * self._rates[currency], 2)

    @staticmethod
    def _seeded_time(seed: int, start_hour: int) -> str:
        hour = (start_hour + (seed % 8)) % 24
        minute = (seed % 4) * 15
        return f"{hour:02d}:{minute:02d}"

    @staticmethod
    def _arrival_time(departure_time: str, duration_minutes: int) -> str:
        hour, minute = (int(part) for part in departure_time.split(":"))
        total_minutes = (hour * 60) + minute + duration_minutes
        arrival_hour = (total_minutes // 60) % 24
        arrival_minute = total_minutes % 60
        return f"{arrival_hour:02d}:{arrival_minute:02d}"

    @staticmethod
    def _haversine_km(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
    ) -> float:
        earth_radius_km = 6371.0
        lat1 = math.radians(origin_latitude)
        lon1 = math.radians(origin_longitude)
        lat2 = math.radians(destination_latitude)
        lon2 = math.radians(destination_longitude)

        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1
        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return earth_radius_km * c

    @staticmethod
    def _shift_time(value: str, hour_delta: int) -> str:
        hour, minute = (int(part) for part in value.split(":"))
        shifted_hour = (hour + hour_delta) % 24
        return f"{shifted_hour:02d}:{minute:02d}"
