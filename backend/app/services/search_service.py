from __future__ import annotations

from itertools import product

from fastapi import HTTPException, status

from app.models import FlightOffer, RouteResult, SearchRequest, SearchResponse
from app.providers.flight_provider import FlightProvider, FlightProviderError
from app.services.airport_service import AirportExpansionService, UnknownCityError
from app.services.currency_service import CurrencyService, UnsupportedCurrencyError
from app.services.sort_service import SortService


class FlightSearchService:
    def __init__(
        self,
        provider: FlightProvider,
        airport_service: AirportExpansionService,
        currency_service: CurrencyService,
        sort_service: SortService,
    ) -> None:
        self._provider = provider
        self._airport_service = airport_service
        self._currency_service = currency_service
        self._sort_service = sort_service

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    def search(self, request: SearchRequest) -> SearchResponse:
        try:
            expanded_origins = self._airport_service.expand(request.normalized_origin_city)
            expanded_destinations = self._airport_service.expand(
                request.normalized_destination_city
            )
            display_currency = self._currency_service.resolve_display_currency(
                currency_mode=request.currency_mode,
                origin_city=request.normalized_origin_city,
                destination_city=request.normalized_destination_city,
                explicit_currency=request.normalized_currency,
            )
        except (UnknownCityError, UnsupportedCurrencyError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except FlightProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        route_results: list[RouteResult] = []
        all_offers: list[FlightOffer] = []

        try:
            for origin_airport in expanded_origins:
                for destination_airport in expanded_destinations:
                    outbound_options = self._provider.search_one_way(
                        request, origin_airport, destination_airport
                    )

                    if request.trip_type == "round_trip":
                        return_options = self._provider.search_one_way(
                            request, destination_airport, origin_airport
                        )
                        hydrated_offers = self._build_round_trip_offers(
                            request=request,
                            origin_airport=origin_airport,
                            destination_airport=destination_airport,
                            outbound_options=outbound_options,
                            return_options=return_options,
                        )
                    else:
                        hydrated_offers = self._build_one_way_offers(
                            request=request,
                            direction="outbound",
                            raw_offers=outbound_options,
                        )

                    for offer in hydrated_offers:
                        offer.display_currency = display_currency
                        offer.display_price = self._currency_service.convert(
                            amount=offer.original_price,
                            source_currency=offer.original_currency,
                            target_currency=display_currency,
                        )

                    hydrated_offers = self._sort_service.rank(hydrated_offers, request.sort_mode)

                    route_results.append(
                        RouteResult(
                            route_key=f"{origin_airport}-{destination_airport}",
                            origin_airport=origin_airport,
                            destination_airport=destination_airport,
                            offers=hydrated_offers,
                        )
                    )
                    all_offers.extend(hydrated_offers)
        except FlightProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        sorted_offers = self._sort_service.rank(all_offers, request.sort_mode)
        if sorted_offers:
            cheapest_offer = min(sorted_offers, key=lambda offer: offer.display_price or 0.0)
            cheapest_offer.is_best_price = True

        return SearchResponse(
            expanded_origin_airports=expanded_origins,
            expanded_destination_airports=expanded_destinations,
            display_currency=display_currency,
            route_results=route_results,
            best_results=sorted_offers,
        )

    def _build_one_way_offers(
        self,
        request: SearchRequest,
        direction: str,
        raw_offers: list[dict],
    ) -> list[FlightOffer]:
        offers = [
            FlightOffer(
                provider=raw_offer["provider"],
                airline=raw_offer["airline"],
                origin_airport=raw_offer["origin_airport"],
                destination_airport=raw_offer["destination_airport"],
                trip_type="one_way",
                cabin_class=request.cabin_class,
                direct=int(raw_offer["stops"]) == 0,
                total_stops=int(raw_offer["stops"]),
                max_segment_stops=int(raw_offer["stops"]),
                total_duration_minutes=int(raw_offer["duration_minutes"]),
                original_price=float(raw_offer["original_price"]),
                original_currency=raw_offer["original_currency"],
                purchase_link=raw_offer.get("purchase_link"),
                segments=[
                    {
                        "direction": direction,
                        "airline": raw_offer["airline"],
                        "origin_airport": raw_offer["origin_airport"],
                        "destination_airport": raw_offer["destination_airport"],
                        "departure_time": raw_offer["departure_time"],
                        "arrival_time": raw_offer["arrival_time"],
                        "duration_minutes": int(raw_offer["duration_minutes"]),
                        "stops": int(raw_offer["stops"]),
                        "purchase_link": raw_offer.get("purchase_link"),
                    }
                ],
            )
            for raw_offer in raw_offers
        ]

        return self._filter_by_max_stops(offers, request.max_stops)

    def _build_round_trip_offers(
        self,
        request: SearchRequest,
        origin_airport: str,
        destination_airport: str,
        outbound_options: list[dict],
        return_options: list[dict],
    ) -> list[FlightOffer]:
        combined_offers: list[FlightOffer] = []

        for outbound_option, return_option in product(outbound_options, return_options):
            outbound_stops = int(outbound_option["stops"])
            return_stops = int(return_option["stops"])
            if request.max_stops is not None and max(outbound_stops, return_stops) > request.max_stops:
                continue

            total_price, original_currency = self._combine_original_prices(
                float(outbound_option["original_price"]),
                outbound_option["original_currency"],
                float(return_option["original_price"]),
                return_option["original_currency"],
            )

            segments = [
                {
                    "direction": "outbound",
                    "airline": outbound_option["airline"],
                    "origin_airport": origin_airport,
                    "destination_airport": destination_airport,
                    "departure_time": outbound_option["departure_time"],
                    "arrival_time": outbound_option["arrival_time"],
                    "duration_minutes": int(outbound_option["duration_minutes"]),
                    "stops": outbound_stops,
                    "purchase_link": outbound_option.get("purchase_link"),
                },
                {
                    "direction": "return",
                    "airline": return_option["airline"],
                    "origin_airport": destination_airport,
                    "destination_airport": origin_airport,
                    "departure_time": return_option["departure_time"],
                    "arrival_time": return_option["arrival_time"],
                    "duration_minutes": int(return_option["duration_minutes"]),
                    "stops": return_stops,
                    "purchase_link": return_option.get("purchase_link"),
                },
            ]

            airlines = [segment["airline"] for segment in segments]
            purchase_link = self._combine_purchase_links(
                outbound_option.get("purchase_link"),
                return_option.get("purchase_link"),
                airlines,
            )

            combined_offers.append(
                FlightOffer(
                    provider=outbound_option["provider"],
                    airline=" / ".join(dict.fromkeys(airlines)),
                    origin_airport=origin_airport,
                    destination_airport=destination_airport,
                    trip_type="round_trip",
                    cabin_class=request.cabin_class,
                    direct=outbound_stops == 0 and return_stops == 0,
                    total_stops=outbound_stops + return_stops,
                    max_segment_stops=max(outbound_stops, return_stops),
                    total_duration_minutes=(
                        int(outbound_option["duration_minutes"])
                        + int(return_option["duration_minutes"])
                    ),
                    original_price=total_price,
                    original_currency=original_currency,
                    purchase_link=purchase_link,
                    segments=segments,
                )
            )

        return combined_offers

    def _combine_original_prices(
        self,
        outbound_price: float,
        outbound_currency: str,
        return_price: float,
        return_currency: str,
    ) -> tuple[float, str]:
        if outbound_currency == return_currency:
            return round(outbound_price + return_price, 2), outbound_currency

        normalized_return_price = self._currency_service.convert(
            amount=return_price,
            source_currency=return_currency,
            target_currency=outbound_currency,
        )
        return round(outbound_price + normalized_return_price, 2), outbound_currency

    @staticmethod
    def _combine_purchase_links(
        outbound_link: str | None,
        return_link: str | None,
        airlines: list[str],
    ) -> str | None:
        if len(set(airlines)) == 1 and outbound_link:
            return outbound_link
        if outbound_link and return_link and outbound_link == return_link:
            return outbound_link
        return None

    @staticmethod
    def _filter_by_max_stops(
        offers: list[FlightOffer],
        max_stops: int | None,
    ) -> list[FlightOffer]:
        if max_stops is None:
            return offers
        return [offer for offer in offers if offer.max_segment_stops <= max_stops]
