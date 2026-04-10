from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from app.city_normalizer import normalize_city_name
from app.config_loader import load_airport_rows, load_country_currency_map
from app.models import AirportSuggestion


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return " ".join(without_marks.casefold().replace("-", " ").split())


@dataclass(frozen=True)
class AirportRecord:
    name: str
    city: str
    country: str
    iata: str
    icao: str
    latitude: float
    longitude: float
    timezone: str


class AirportCatalogService:
    def __init__(self) -> None:
        rows = load_airport_rows()
        self._airports = [
            AirportRecord(
                name=row["name"],
                city=row["city"],
                country=row["country"],
                iata=row["iata"],
                icao=row["icao"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                timezone=row["timezone"],
            )
            for row in rows
        ]
        self._country_currency_map = load_country_currency_map()
        self._by_iata = {airport.iata: airport for airport in self._airports}
        self._city_groups: dict[tuple[str, str], list[AirportRecord]] = {}
        self._city_name_to_groups: dict[str, list[list[AirportRecord]]] = {}

        for airport in self._airports:
            city_key = (_normalize_text(airport.city), airport.country)
            self._city_groups.setdefault(city_key, []).append(airport)

        for (normalized_city, _country), airports in self._city_groups.items():
            self._city_name_to_groups.setdefault(normalized_city, []).append(airports)

    def get_airport(self, code: str) -> AirportRecord | None:
        return self._by_iata.get(code.strip().upper())

    def expand_city_or_airport(self, query: str, limit: int = 3) -> list[str]:
        cleaned = query.strip()
        upper_query = cleaned.upper()
        if len(upper_query) == 3 and upper_query in self._by_iata:
            return [upper_query]

        normalized_query = _normalize_text(normalize_city_name(cleaned))
        airport_group = self._best_city_group(normalized_query)
        if airport_group:
            return [airport.iata for airport in self._rank_airports(airport_group)[:limit]]

        airport_matches = [
            airport
            for airport in self._airports
            if _normalize_text(airport.name) == normalized_query
        ]
        if airport_matches:
            return [airport.iata for airport in self._rank_airports(airport_matches)[:limit]]

        return []

    def suggest(self, query: str, limit: int = 8) -> list[AirportSuggestion]:
        cleaned = query.strip()
        if len(cleaned) < 2:
            return []

        normalized_query = _normalize_text(cleaned)
        suggestions: list[tuple[float, AirportSuggestion]] = []
        seen_values: set[str] = set()

        for (normalized_city, country), airports in self._city_groups.items():
            if normalized_query not in normalized_city:
                continue

            ranked_airports = self._rank_airports(airports)
            airport_codes = [airport.iata for airport in ranked_airports[:3]]
            first_airport = ranked_airports[0]
            value = first_airport.city
            unique_key = f"city:{first_airport.city}:{country}"
            if unique_key in seen_values:
                continue

            label = f"{first_airport.city}, {country} ({', '.join(airport_codes)})"
            score = self._score_match(normalized_query, normalized_city)
            suggestions.append(
                (
                    score,
                    AirportSuggestion(
                        kind="city",
                        value=value,
                        label=label,
                        airport_codes=airport_codes,
                        city=first_airport.city,
                        country=country,
                    ),
                )
            )
            seen_values.add(unique_key)

        for airport in self._airports:
            airport_name = _normalize_text(airport.name)
            airport_city = _normalize_text(airport.city)
            airport_iata = airport.iata.lower()
            if (
                normalized_query not in airport_name
                and normalized_query not in airport_city
                and normalized_query not in airport_iata
            ):
                continue

            unique_key = f"airport:{airport.iata}"
            if unique_key in seen_values:
                continue

            label = f"{airport.name} ({airport.iata}) - {airport.city}, {airport.country}"
            score = min(
                self._score_match(normalized_query, airport_name),
                self._score_match(normalized_query, airport_city),
                self._score_match(normalized_query, airport_iata),
            )
            suggestions.append(
                (
                    score,
                    AirportSuggestion(
                        kind="airport",
                        value=airport.iata,
                        label=label,
                        airport_codes=[airport.iata],
                        city=airport.city,
                        country=airport.country,
                    ),
                )
            )
            seen_values.add(unique_key)

        suggestions.sort(key=lambda item: (item[0], item[1].label))
        return [suggestion for _, suggestion in suggestions[:limit]]

    def resolve_currency_code(self, query: str) -> str | None:
        cleaned = query.strip()
        upper_query = cleaned.upper()
        airport = self._by_iata.get(upper_query)
        if airport:
            return self._country_currency_map.get(airport.country)

        normalized_query = _normalize_text(normalize_city_name(cleaned))
        airport_group = self._best_city_group(normalized_query)
        if not airport_group:
            return None

        country = self._rank_airports(airport_group)[0].country
        return self._country_currency_map.get(country)

    @staticmethod
    def _score_match(query: str, target: str) -> float:
        if target.startswith(query):
            return 0.0
        if f" {query}" in target:
            return 1.0
        return 2.0

    @staticmethod
    def _rank_airports(airports: list[AirportRecord]) -> list[AirportRecord]:
        return sorted(
            airports,
            key=lambda airport: (
                0 if "international" in airport.name.lower() else 1,
                0 if airport.iata else 1,
                len(airport.name),
                airport.iata,
            ),
        )

    def _best_city_group(self, normalized_city: str) -> list[AirportRecord]:
        groups = self._city_name_to_groups.get(normalized_city, [])
        if not groups:
            return []

        ranked_groups = sorted(
            groups,
            key=lambda airports: (
                -sum(1 for airport in airports if "international" in airport.name.lower()),
                -len(airports),
                len(self._rank_airports(airports)[0].name),
                self._rank_airports(airports)[0].country,
            ),
        )
        return ranked_groups[0]
