from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


TripType = Literal["one_way", "round_trip"]
CabinClass = Literal["economy", "business"]
CurrencyMode = Literal["origin", "destination", "custom"]
SortMode = Literal["cheapest", "shortest", "best_value"]


class SearchRequest(BaseModel):
    origin_city: str = Field(..., min_length=1)
    destination_city: str = Field(..., min_length=1)
    departure_date: date
    return_date: date | None = None
    trip_type: TripType
    cabin_class: CabinClass
    currency_mode: CurrencyMode
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    sort_mode: SortMode = "cheapest"
    max_stops: int | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_trip_dates(self) -> "SearchRequest":
        if self.trip_type == "round_trip" and self.return_date is None:
            raise ValueError("return_date is required when trip_type is round_trip")

        if self.return_date and self.return_date < self.departure_date:
            raise ValueError("return_date must be on or after departure_date")

        if self.currency_mode == "custom" and not self.currency:
            raise ValueError("currency is required when currency_mode is custom")

        return self

    @property
    def normalized_origin_city(self) -> str:
        return self.origin_city.strip()

    @property
    def normalized_destination_city(self) -> str:
        return self.destination_city.strip()

    @property
    def normalized_currency(self) -> str | None:
        return self.currency.upper() if self.currency else None


class FlightSegment(BaseModel):
    direction: Literal["outbound", "return"]
    airline: str
    origin_airport: str
    destination_airport: str
    departure_time: str
    arrival_time: str
    duration_minutes: int
    stops: int
    purchase_link: str | None = None


class FlightOffer(BaseModel):
    provider: str
    airline: str
    origin_airport: str
    destination_airport: str
    trip_type: TripType
    cabin_class: CabinClass
    direct: bool
    total_stops: int
    max_segment_stops: int
    total_duration_minutes: int
    original_price: float
    original_currency: str
    purchase_link: str | None = None
    segments: list[FlightSegment]
    display_price: float | None = None
    display_currency: str | None = None
    ranking_score: float | None = None
    is_best_price: bool = False


class RouteResult(BaseModel):
    route_key: str
    origin_airport: str
    destination_airport: str
    offers: list[FlightOffer]


class SearchResponse(BaseModel):
    expanded_origin_airports: list[str]
    expanded_destination_airports: list[str]
    display_currency: str
    route_results: list[RouteResult]
    best_results: list[FlightOffer]


class AirportSuggestion(BaseModel):
    kind: Literal["city", "airport"]
    value: str
    label: str
    airport_codes: list[str]
    city: str
    country: str
