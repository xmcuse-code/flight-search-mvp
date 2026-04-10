from __future__ import annotations

from fastapi import FastAPI
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware

from app.models import AirportSuggestion, SearchRequest, SearchResponse
from app.providers.factory import create_flight_provider
from app.services.airport_service import AirportExpansionService
from app.services.currency_service import CurrencyService
from app.services.search_service import FlightSearchService
from app.services.sort_service import SortService
from app.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="Flight Search MVP API",
    version="0.1.0",
    description="Mock multi-origin / multi-destination flight search API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

airport_service = AirportExpansionService()
currency_service = CurrencyService()
sort_service = SortService()

search_service = FlightSearchService(
    provider=create_flight_provider(settings),
    airport_service=airport_service,
    currency_service=currency_service,
    sort_service=sort_service,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.environment,
        "configured_provider": settings.flight_provider,
        "active_provider": search_service.provider_name,
    }


@app.get("/airport-suggestions", response_model=list[AirportSuggestion])
def airport_suggestions(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=8, ge=1, le=12),
) -> list[AirportSuggestion]:
    return airport_service.suggest(q, limit)


@app.post("/search-flights", response_model=SearchResponse)
def search_flights(request: SearchRequest) -> SearchResponse:
    return search_service.search(request)
