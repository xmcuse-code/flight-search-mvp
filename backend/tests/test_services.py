from __future__ import annotations

import unittest
from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.models import FlightOffer, SearchRequest
from app.providers.amadeus_provider import AmadeusFlightProvider
from app.providers.factory import create_flight_provider
from app.providers.duffel_provider import DuffelFlightProvider
from app.providers.mock_provider import MockFlightProvider
from app.services.airport_service import AirportExpansionService
from app.services.currency_service import CurrencyService
from app.services.search_service import FlightSearchService
from app.services.sort_service import SortService
from app.settings import Settings


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
    def test_health_endpoint_exposes_provider_state(self) -> None:
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("configured_provider", data)
        self.assertIn("active_provider", data)

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


class ProviderFactoryTests(unittest.TestCase):
    def test_factory_defaults_to_mock_provider(self) -> None:
        provider = create_flight_provider(
            Settings(
                environment="development",
                host="0.0.0.0",
                port=8000,
                cors_allow_origins=["http://localhost:5173"],
                flight_provider="mock",
                duffel_access_token=None,
                duffel_base_url="https://api.duffel.com",
                duffel_version="v2",
                duffel_timeout_seconds=20.0,
                amadeus_client_id=None,
                amadeus_client_secret=None,
                amadeus_base_url="https://test.api.amadeus.com",
                amadeus_timeout_seconds=15.0,
            )
        )
        self.assertEqual(provider.provider_name, "mock_flights")

    def test_amadeus_offer_mapping(self) -> None:
        mapped = AmadeusFlightProvider._map_offer(
            raw_offer={
                "itineraries": [
                    {
                        "duration": "PT2H45M",
                        "segments": [
                            {
                                "departure": {"iataCode": "NRT", "at": "2026-05-01T09:15:00"},
                                "arrival": {"iataCode": "TPE", "at": "2026-05-01T12:00:00"},
                                "carrierCode": "CI",
                            }
                        ],
                    }
                ],
                "validatingAirlineCodes": ["CI"],
                "price": {"grandTotal": "312.40", "currency": "USD"},
            },
            provider_name="amadeus_test",
            carrier_lookup={"CI": "China Airlines"},
        )
        self.assertIsNotNone(mapped)
        self.assertEqual(mapped["airline"], "China Airlines")
        self.assertEqual(mapped["duration_minutes"], 165)
        self.assertEqual(mapped["stops"], 0)

    def test_factory_can_build_duffel_provider(self) -> None:
        provider = create_flight_provider(
            Settings(
                environment="development",
                host="0.0.0.0",
                port=8000,
                cors_allow_origins=["http://localhost:5173"],
                flight_provider="duffel",
                duffel_access_token="test_token",
                duffel_base_url="https://api.duffel.com",
                duffel_version="v2",
                duffel_timeout_seconds=20.0,
                amadeus_client_id=None,
                amadeus_client_secret=None,
                amadeus_base_url="https://test.api.amadeus.com",
                amadeus_timeout_seconds=15.0,
            )
        )
        self.assertEqual(provider.provider_name, "duffel_test")

    def test_duffel_offer_mapping(self) -> None:
        mapped = DuffelFlightProvider._map_offer(
            {
                "total_amount": "312.40",
                "total_currency": "USD",
                "slices": [
                    {
                        "segments": [
                            {
                                "departing_at": "2026-05-01T09:15:00Z",
                                "arriving_at": "2026-05-01T12:00:00Z",
                                "origin": {"iata_code": "NRT"},
                                "destination": {"iata_code": "TPE"},
                                "operating_carrier": {"name": "China Airlines"},
                            }
                        ]
                    }
                ],
            },
            "duffel_test",
        )
        self.assertIsNotNone(mapped)
        self.assertEqual(mapped["airline"], "China Airlines")
        self.assertEqual(mapped["origin_airport"], "NRT")
        self.assertEqual(mapped["destination_airport"], "TPE")
        self.assertEqual(mapped["duration_minutes"], 165)
        self.assertEqual(mapped["stops"], 0)


if __name__ == "__main__":
    unittest.main()
