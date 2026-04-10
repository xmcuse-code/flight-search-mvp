from __future__ import annotations

import unittest
from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.models import FlightOffer, SearchRequest
from app.providers.mock_provider import MockFlightProvider
from app.services.airport_service import AirportExpansionService
from app.services.currency_service import CurrencyService
from app.services.search_service import FlightSearchService
from app.services.sort_service import SortService


class AirportExpansionServiceTests(unittest.TestCase):
    def test_expand_known_city(self) -> None:
        service = AirportExpansionService()
        self.assertEqual(service.expand("Wuhan"), ["WUH", "CSX", "KHN"])

    def test_expand_chinese_alias(self) -> None:
        service = AirportExpansionService()
        self.assertEqual(service.expand("武漢"), ["WUH", "CSX", "KHN"])

    def test_expand_global_city_from_catalog(self) -> None:
        service = AirportExpansionService()
        airports = service.expand("Paris")
        self.assertIn("CDG", airports)

    def test_global_suggestions_include_airports(self) -> None:
        service = AirportExpansionService()
        suggestions = service.suggest("Tok", limit=5)
        self.assertGreater(len(suggestions), 0)
        self.assertTrue(any("Tokyo" in suggestion.label for suggestion in suggestions))

    def test_chinese_query_does_not_match_everything(self) -> None:
        service = AirportExpansionService()
        suggestions = service.suggest("武漢", limit=5)
        self.assertGreater(len(suggestions), 0)
        self.assertTrue(all("Wuhan" in suggestion.label or "武漢" in suggestion.label for suggestion in suggestions))


class CurrencyServiceTests(unittest.TestCase):
    def test_convert_cny_to_twd(self) -> None:
        service = CurrencyService()
        self.assertEqual(service.convert(720, "CNY", "TWD"), 3200.0)


class SortServiceTests(unittest.TestCase):
    def test_cheapest_ranking_prefers_lower_price(self) -> None:
        offers = [
            FlightOffer(
                provider="mock",
                airline="A",
                origin_airport="WUH",
                destination_airport="TPE",
                trip_type="one_way",
                cabin_class="economy",
                direct=True,
                total_stops=0,
                max_segment_stops=0,
                total_duration_minutes=160,
                original_price=100,
                original_currency="CNY",
                display_price=500.0,
                display_currency="TWD",
                segments=[],
            ),
            FlightOffer(
                provider="mock",
                airline="B",
                origin_airport="CSX",
                destination_airport="TPE",
                trip_type="one_way",
                cabin_class="economy",
                direct=False,
                total_stops=1,
                max_segment_stops=1,
                total_duration_minutes=140,
                original_price=120,
                original_currency="CNY",
                display_price=450.0,
                display_currency="TWD",
                segments=[],
            ),
        ]
        ranked = SortService().rank(offers, "cheapest")
        self.assertEqual(ranked[0].airline, "B")


class SearchApiTests(unittest.TestCase):
    def test_search_endpoint_returns_sorted_results(self) -> None:
        client = TestClient(app)
        payload = {
            "origin_city": "Wuhan",
            "destination_city": "Taipei",
            "departure_date": "2026-05-01",
            "return_date": "2026-05-05",
            "trip_type": "round_trip",
            "cabin_class": "economy",
            "currency_mode": "destination",
            "currency": "TWD",
            "sort_mode": "cheapest",
            "max_stops": None,
        }

        response = client.post("/search-flights", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["expanded_origin_airports"], ["WUH", "CSX", "KHN"])
        self.assertEqual(data["display_currency"], "TWD")
        self.assertGreater(len(data["best_results"]), 0)
        self.assertTrue(data["best_results"][0]["display_price"] <= data["best_results"][1]["display_price"])

    def test_search_endpoint_supports_global_city_queries(self) -> None:
        client = TestClient(app)
        payload = {
            "origin_city": "Paris",
            "destination_city": "Tokyo",
            "departure_date": "2026-06-01",
            "return_date": "2026-06-10",
            "trip_type": "round_trip",
            "cabin_class": "economy",
            "currency_mode": "destination",
            "currency": None,
            "sort_mode": "cheapest",
            "max_stops": 1,
        }

        response = client.post("/search-flights", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data["expanded_origin_airports"]), 0)
        self.assertGreater(len(data["expanded_destination_airports"]), 0)
        self.assertGreater(len(data["best_results"]), 0)


class SearchServiceTests(unittest.TestCase):
    def test_search_service_marks_best_price(self) -> None:
        service = FlightSearchService(
            provider=MockFlightProvider(),
            airport_service=AirportExpansionService(),
            currency_service=CurrencyService(),
            sort_service=SortService(),
        )
        request = SearchRequest(
            origin_city="Wuhan",
            destination_city="Taipei",
            departure_date=date(2026, 5, 1),
            return_date=None,
            trip_type="one_way",
            cabin_class="economy",
            currency_mode="destination",
            sort_mode="cheapest",
            max_stops=None,
        )

        response = service.search(request)
        self.assertEqual(sum(1 for offer in response.best_results if offer.is_best_price), 1)

    def test_search_service_filters_by_max_stops_per_segment(self) -> None:
        service = FlightSearchService(
            provider=MockFlightProvider(),
            airport_service=AirportExpansionService(),
            currency_service=CurrencyService(),
            sort_service=SortService(),
        )
        request = SearchRequest(
            origin_city="Wuhan",
            destination_city="Taipei",
            departure_date=date(2026, 5, 1),
            return_date=None,
            trip_type="one_way",
            cabin_class="economy",
            currency_mode="destination",
            sort_mode="cheapest",
            max_stops=0,
        )

        response = service.search(request)
        self.assertTrue(all(offer.max_segment_stops == 0 for offer in response.best_results))

    def test_round_trip_search_can_mix_outbound_and_return_patterns(self) -> None:
        service = FlightSearchService(
            provider=MockFlightProvider(),
            airport_service=AirportExpansionService(),
            currency_service=CurrencyService(),
            sort_service=SortService(),
        )
        request = SearchRequest(
            origin_city="Wuhan",
            destination_city="Taipei",
            departure_date=date(2026, 5, 1),
            return_date=date(2026, 5, 5),
            trip_type="round_trip",
            cabin_class="economy",
            currency_mode="destination",
            sort_mode="cheapest",
            max_stops=1,
        )

        response = service.search(request)
        mixed_patterns = [
            offer
            for offer in response.best_results
            if len(offer.segments) == 2 and offer.segments[0].stops != offer.segments[1].stops
        ]
        self.assertGreater(len(mixed_patterns), 0)


if __name__ == "__main__":
    unittest.main()
