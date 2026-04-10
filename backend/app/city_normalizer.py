from __future__ import annotations

from functools import lru_cache

from app.config_loader import _load_json


@lru_cache
def _load_city_aliases() -> dict[str, str]:
    data = _load_json("city_aliases.json")
    return {key.lower(): value for key, value in data.items()}


def normalize_city_name(city: str) -> str:
    cleaned = city.strip()
    alias = _load_city_aliases().get(cleaned.lower())
    if alias:
        return alias
    return cleaned.title()
