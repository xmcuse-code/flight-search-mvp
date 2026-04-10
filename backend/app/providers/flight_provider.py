from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import SearchRequest


class FlightProvider(ABC):
    provider_name: str

    @abstractmethod
    def search_one_way(
        self,
        request: SearchRequest,
        origin_airport: str,
        destination_airport: str,
    ) -> list[dict]:
        """Return raw one-way flight offers for a route."""
