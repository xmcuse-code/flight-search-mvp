import type {
  AirportSuggestion,
  SearchRequestPayload,
  SearchResponse,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function searchFlights(
  payload: SearchRequestPayload,
): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE_URL}/search-flights`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = "Search failed. Please try again.";
    try {
      const data = (await response.json()) as { detail?: string };
      if (data.detail) {
        message = data.detail;
      }
    } catch {
      // Keep the generic message when the backend response is not JSON.
    }
    throw new Error(message);
  }

  return (await response.json()) as SearchResponse;
}

export async function fetchAirportSuggestions(
  query: string,
): Promise<AirportSuggestion[]> {
  const response = await fetch(
    `${API_BASE_URL}/airport-suggestions?q=${encodeURIComponent(query)}`,
  );
  if (!response.ok) {
    return [];
  }
  return (await response.json()) as AirportSuggestion[];
}
