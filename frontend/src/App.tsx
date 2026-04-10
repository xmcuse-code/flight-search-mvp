import type { FormEvent } from "react";
import { useRef, useState } from "react";

import { ResultsList } from "./components/ResultsList";
import { SearchForm } from "./components/SearchForm";
import { searchFlights } from "./lib/api";
import type { SearchRequestPayload, SearchResponse } from "./lib/types";

const initialForm: SearchRequestPayload = {
  origin_city: "武漢",
  destination_city: "台北",
  departure_date: "2026-05-01",
  return_date: "2026-05-05",
  trip_type: "round_trip",
  cabin_class: "economy",
  currency_mode: "destination",
  currency: null,
  sort_mode: "cheapest",
  max_stops: null,
};

function App() {
  const [form, setForm] = useState<SearchRequestPayload>(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [formCollapsed, setFormCollapsed] = useState(false);
  const resultsAnchorRef = useRef<HTMLDivElement | null>(null);

  const handleChange = (
    field: keyof SearchRequestPayload,
    value: SearchRequestPayload[keyof SearchRequestPayload],
  ) => {
    setForm((previous) => {
      const next = { ...previous, [field]: value };

      if (field === "trip_type" && value === "one_way") {
        next.return_date = null;
      }

      if (field === "currency_mode" && value !== "custom") {
        next.currency = null;
      }

      return next;
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await runSearch();
  };

  const runSearch = async () => {
    setLoading(true);
    setError(null);
    setResults(null);

    const payload: SearchRequestPayload = {
      ...form,
      currency: form.currency_mode === "custom" ? form.currency : null,
      return_date: form.trip_type === "round_trip" ? form.return_date : null,
    };

    try {
      const data = await searchFlights(payload);
      setResults(data);
      setFormCollapsed(true);
      window.setTimeout(() => {
        resultsAnchorRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 80);
    } catch (submitError) {
      if (submitError instanceof Error) {
        setError(submitError.message);
      } else {
        setError("Search failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <SearchForm
        form={form}
        loading={loading}
        collapsed={formCollapsed}
        onChange={handleChange}
        onSubmit={handleSubmit}
        onToggleCollapsed={() => setFormCollapsed((previous) => !previous)}
        onQuickSearch={() => {
          void runSearch();
        }}
      />

      {error ? <p className="error-banner">{error}</p> : null}
      <div ref={resultsAnchorRef}>
        <ResultsList data={results} />
      </div>
    </main>
  );
}

export default App;
