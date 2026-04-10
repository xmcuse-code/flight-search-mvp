from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent


def _resolve_config_path(filename: str) -> Path:
    candidate_paths = [
        BACKEND_DIR / "config" / filename,
        PROJECT_DIR / "config" / filename,
    ]
    for path in candidate_paths:
        if path.exists():
            return path
    return candidate_paths[0]


def _load_json(filename: str) -> dict[str, Any]:
    path = _resolve_config_path(filename)
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_text(filename: str) -> str:
    path = _resolve_config_path(filename)
    return path.read_text(encoding="utf-8")


@lru_cache
def load_city_airports() -> dict[str, list[str]]:
    data = _load_json("city_airports.json")
    return {city: [code.upper() for code in airports] for city, airports in data.items()}


@lru_cache
def load_city_currencies() -> dict[str, str]:
    data = _load_json("city_currencies.json")
    return {city: currency.upper() for city, currency in data.items()}


@lru_cache
def load_currency_rates() -> dict[str, float]:
    data = _load_json("currency_rates.json")
    return {currency.upper(): float(rate) for currency, rate in data.items()}


@lru_cache
def load_mock_flights() -> dict[str, list[dict[str, Any]]]:
    data = _load_json("mock_flights.json")
    return {route.upper(): offers for route, offers in data.items()}


@lru_cache
def load_airport_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reader = csv.reader(_load_text("openflights_airports.dat").splitlines())
    for raw_row in reader:
        if len(raw_row) < 14:
            continue

        iata = raw_row[4].strip()
        if iata == r"\N" or len(iata) != 3:
            continue

        airport_type = raw_row[12].strip().lower()
        if airport_type != "airport":
            continue

        try:
            latitude = float(raw_row[6])
            longitude = float(raw_row[7])
        except ValueError:
            continue

        rows.append(
            {
                "id": raw_row[0],
                "name": raw_row[1].strip(),
                "city": raw_row[2].strip(),
                "country": raw_row[3].strip(),
                "iata": iata.upper(),
                "icao": raw_row[5].strip(),
                "latitude": latitude,
                "longitude": longitude,
                "timezone": raw_row[11].strip(),
                "source": raw_row[13].strip(),
            }
        )

    return rows


@lru_cache
def load_country_currency_map() -> dict[str, str]:
    data = _load_json("countries.json")
    country_currency_map: dict[str, str] = {}

    for country in data:
        country_name = country.get("name", {}).get("common")
        currencies = country.get("currencies", {})
        if not country_name or not currencies:
            continue

        first_currency_code = next(iter(currencies.keys()), None)
        if first_currency_code:
            country_currency_map[str(country_name)] = str(first_currency_code).upper()

    return country_currency_map
