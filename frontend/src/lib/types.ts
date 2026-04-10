export type TripType = "one_way" | "round_trip";
export type CabinClass = "economy" | "business";
export type CurrencyMode = "origin" | "destination" | "custom";
export type SortMode = "cheapest" | "shortest" | "best_value";

export interface AirportSuggestion {
  kind: "city" | "airport";
  value: string;
  label: string;
  airport_codes: string[];
  city: string;
  country: string;
}

export interface SearchRequestPayload {
  origin_city: string;
  destination_city: string;
  departure_date: string;
  return_date: string | null;
  trip_type: TripType;
  cabin_class: CabinClass;
  currency_mode: CurrencyMode;
  currency: string | null;
  sort_mode: SortMode;
  max_stops: 0 | 1 | null;
}

export interface FlightSegment {
  direction: "outbound" | "return";
  airline: string;
  origin_airport: string;
  destination_airport: string;
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  stops: number;
  purchase_link?: string | null;
}

export interface FlightOffer {
  provider: string;
  airline: string;
  origin_airport: string;
  destination_airport: string;
  trip_type: TripType;
  cabin_class: CabinClass;
  direct: boolean;
  total_stops: number;
  max_segment_stops: number;
  total_duration_minutes: number;
  original_price: number;
  original_currency: string;
  purchase_link?: string | null;
  segments: FlightSegment[];
  display_price?: number | null;
  display_currency?: string | null;
  ranking_score?: number | null;
  is_best_price: boolean;
}

export interface RouteResult {
  route_key: string;
  origin_airport: string;
  destination_airport: string;
  offers: FlightOffer[];
}

export interface SearchResponse {
  expanded_origin_airports: string[];
  expanded_destination_airports: string[];
  display_currency: string;
  route_results: RouteResult[];
  best_results: FlightOffer[];
}
