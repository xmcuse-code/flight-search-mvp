from __future__ import annotations

from app.models import FlightOffer, SortMode


class SortService:
    def rank(self, offers: list[FlightOffer], mode: SortMode) -> list[FlightOffer]:
        if not offers:
            return []

        priced_offers = [offer for offer in offers if offer.display_price is not None]
        if not priced_offers:
            return offers

        price_values = [offer.display_price or 0.0 for offer in priced_offers]
        duration_values = [offer.total_duration_minutes for offer in priced_offers]

        min_price, max_price = min(price_values), max(price_values)
        min_duration, max_duration = min(duration_values), max(duration_values)

        for offer in priced_offers:
            price_score = self._normalize(offer.display_price or 0.0, min_price, max_price)
            duration_score = self._normalize(
                offer.total_duration_minutes, min_duration, max_duration
            )

            if mode == "cheapest":
                offer.ranking_score = offer.display_price
            elif mode == "shortest":
                offer.ranking_score = float(offer.total_duration_minutes)
            else:
                offer.ranking_score = round((price_score * 0.65) + (duration_score * 0.35), 4)

        if mode == "cheapest":
            return sorted(
                priced_offers,
                key=lambda offer: (
                    offer.display_price or 0.0,
                    offer.total_duration_minutes,
                    offer.total_stops,
                ),
            )

        if mode == "shortest":
            return sorted(
                priced_offers,
                key=lambda offer: (
                    offer.total_duration_minutes,
                    offer.display_price or 0.0,
                    offer.total_stops,
                ),
            )

        return sorted(
            priced_offers,
            key=lambda offer: (
                offer.ranking_score or 0.0,
                offer.display_price or 0.0,
                offer.total_duration_minutes,
            ),
        )

    @staticmethod
    def _normalize(value: float, minimum: float, maximum: float) -> float:
        if maximum == minimum:
            return 0.0
        return (value - minimum) / (maximum - minimum)
