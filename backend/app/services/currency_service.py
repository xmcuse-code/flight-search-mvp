from __future__ import annotations

from app.city_normalizer import normalize_city_name
from app.config_loader import load_city_currencies, load_currency_rates
from app.models import CurrencyMode
from app.services.airport_catalog_service import AirportCatalogService


class UnsupportedCurrencyError(ValueError):
    """Raised when a currency code does not exist in the mock exchange table."""


class CurrencyService:
    def __init__(self) -> None:
        self._city_currencies = load_city_currencies()
        self._rates = load_currency_rates()
        self._catalog_service = AirportCatalogService()

    def resolve_display_currency(
        self,
        currency_mode: CurrencyMode,
        origin_city: str,
        destination_city: str,
        explicit_currency: str | None = None,
    ) -> str:
        origin_city = normalize_city_name(origin_city)
        destination_city = normalize_city_name(destination_city)

        if currency_mode == "origin":
            currency = self._city_currencies.get(origin_city)
            if not currency:
                currency = self._catalog_service.resolve_currency_code(origin_city)
        elif currency_mode == "destination":
            currency = self._city_currencies.get(destination_city)
            if not currency:
                currency = self._catalog_service.resolve_currency_code(destination_city)
        else:
            currency = explicit_currency.upper() if explicit_currency else None

        if not currency or currency not in self._rates:
            if currency_mode in {"origin", "destination"}:
                return "USD"
            raise UnsupportedCurrencyError(
                f"Unsupported currency resolution for mode '{currency_mode}'. "
                "Check config/city_currencies.json or config/currency_rates.json."
            )

        return currency

    def convert(self, amount: float, source_currency: str, target_currency: str) -> float:
        source = source_currency.upper()
        target = target_currency.upper()
        if source not in self._rates or target not in self._rates:
            raise UnsupportedCurrencyError(
                f"Exchange rate missing for {source} or {target}. Update config/currency_rates.json."
            )

        usd_value = amount / self._rates[source]
        converted = usd_value * self._rates[target]
        return round(converted, 2)
