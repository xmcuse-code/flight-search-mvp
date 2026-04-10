from __future__ import annotations

from app.city_normalizer import normalize_city_name
from app.config_loader import load_city_airports
from app.models import AirportSuggestion
from app.services.airport_catalog_service import AirportCatalogService


class UnknownCityError(ValueError):
    """Raised when a city does not exist in the airport mapping."""


class AirportExpansionService:
    def __init__(self) -> None:
        self._city_airports = load_city_airports()
        self._catalog_service = AirportCatalogService()

    def expand(self, city: str) -> list[str]:
        normalized_city = normalize_city_name(city)
        airports = self._city_airports.get(normalized_city)
        if airports:
            return airports

        global_airports = self._catalog_service.expand_city_or_airport(city)
        if global_airports:
            return global_airports

        raise UnknownCityError(
            f"Unknown city or airport '{city}'. Try an airport code like HND or a city name like Tokyo."
        )

    def suggest(self, query: str, limit: int = 8) -> list[AirportSuggestion]:
        manual_city = normalize_city_name(query)
        manual_airports = self._city_airports.get(manual_city)
        suggestions: list[AirportSuggestion] = []
        if manual_airports:
            suggestions.append(
                AirportSuggestion(
                    kind="city",
                    value=manual_city,
                    label=f"{manual_city} ({', '.join(manual_airports)})",
                    airport_codes=manual_airports,
                    city=manual_city,
                    country="Mapped Region",
                )
            )

        remaining = max(limit - len(suggestions), 0)
        if remaining <= 0:
            return suggestions[:limit]

        return suggestions + self._catalog_service.suggest(query, remaining)
