import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useState } from "react";

import { fetchAirportSuggestions } from "../lib/api";
import type { AirportSuggestion } from "../lib/types";
import type { SearchRequestPayload } from "../lib/types";

interface SearchFormProps {
  form: SearchRequestPayload;
  loading: boolean;
  collapsed: boolean;
  onChange: (
    field: keyof SearchRequestPayload,
    value: SearchRequestPayload[keyof SearchRequestPayload],
  ) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onToggleCollapsed: () => void;
  onQuickSearch: () => void;
}

export function SearchForm({
  form,
  loading,
  collapsed,
  onChange,
  onSubmit,
  onToggleCollapsed,
  onQuickSearch,
}: SearchFormProps) {
  const [originSuggestions, setOriginSuggestions] = useState<AirportSuggestion[]>([]);
  const [destinationSuggestions, setDestinationSuggestions] = useState<
    AirportSuggestion[]
  >([]);

  const tripLabel = form.trip_type === "round_trip" ? "來回" : "單程";
  const stopLabel =
    form.max_stops === null
      ? "不限轉機"
      : form.max_stops === 0
        ? "只看直飛"
        : "最多 1 次轉機";
  const cabinLabel = form.cabin_class === "economy" ? "經濟艙" : "商務艙";
  const currencyLabel =
    form.currency_mode === "destination"
      ? "目的地幣別"
      : form.currency_mode === "origin"
        ? "出發地幣別"
        : form.currency ?? "自訂幣別";
  const dateLabel =
    form.trip_type === "round_trip" && form.return_date
      ? `${form.departure_date} - ${form.return_date}`
      : form.departure_date;

  const handleTextChange =
    (field: keyof SearchRequestPayload) =>
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const value = event.target.value;
      if (field === "currency") {
        onChange(field, value ? value.toUpperCase() : null);
        return;
      }
      onChange(field, value as SearchRequestPayload[keyof SearchRequestPayload]);
    };

  useEffect(() => {
    const timeoutId = window.setTimeout(async () => {
      if (form.origin_city.trim().length < 2) {
        setOriginSuggestions([]);
        return;
      }
      setOriginSuggestions(await fetchAirportSuggestions(form.origin_city));
    }, 180);

    return () => window.clearTimeout(timeoutId);
  }, [form.origin_city]);

  useEffect(() => {
    const timeoutId = window.setTimeout(async () => {
      if (form.destination_city.trim().length < 2) {
        setDestinationSuggestions([]);
        return;
      }
      setDestinationSuggestions(await fetchAirportSuggestions(form.destination_city));
    }, 180);

    return () => window.clearTimeout(timeoutId);
  }, [form.destination_city]);

  const applySuggestion = (
    field: "origin_city" | "destination_city",
    suggestion: AirportSuggestion,
  ) => {
    onChange(field, suggestion.value);
    if (field === "origin_city") {
      setOriginSuggestions([]);
      return;
    }
    setDestinationSuggestions([]);
  };

  const renderSuggestions = (
    field: "origin_city" | "destination_city",
    suggestions: AirportSuggestion[],
  ) => {
    if (suggestions.length === 0) {
      return null;
    }

    return (
      <div className="suggestions-list" role="listbox">
        {suggestions.map((suggestion) => (
          <button
            key={`${field}-${suggestion.kind}-${suggestion.value}-${suggestion.label}`}
            className="suggestion-item"
            type="button"
            onMouseDown={(event) => {
              event.preventDefault();
              applySuggestion(field, suggestion);
            }}
          >
            <span className="suggestion-label">{suggestion.label}</span>
            <span className="suggestion-meta">
              {suggestion.kind === "airport" ? "機場" : "城市"}
            </span>
          </button>
        ))}
      </div>
    );
  };

  return (
    <form className={`search-panel${collapsed ? " collapsed" : ""}`} onSubmit={onSubmit}>
      <div className="search-panel-header">
        <div className="hero-copy">
          {!collapsed ? (
            <>
              <p className="eyebrow">Flight Price Finder</p>
              <h1>多出發地 / 多目的地 / 多幣別 找最低票價</h1>
              <p className="supporting-text">
                輸入城市後，系統會自動展開附近機場並比較所有組合。
              </p>
            </>
          ) : (
            <div className="compact-route">
              <div className="compact-route-main">
                <strong>{form.origin_city || "出發地"}</strong>
                <span className="summary-arrow">→</span>
                <strong>{form.destination_city || "目的地"}</strong>
              </div>
              <div className="compact-route-meta">
                <span>{dateLabel}</span>
                <span>{tripLabel}</span>
                <span>{cabinLabel}</span>
                <span>{stopLabel}</span>
                <span>{currencyLabel}</span>
              </div>
            </div>
          )}
        </div>
        <div className="panel-actions">
          <button
            className="panel-toggle"
            type="button"
            onClick={onToggleCollapsed}
          >
            {collapsed ? "修改條件" : "收合條件"}
          </button>
          {collapsed ? (
            <button className="panel-primary-action" type="button" onClick={onToggleCollapsed}>
              新搜尋
            </button>
          ) : null}
        </div>
      </div>

      {collapsed ? (
        <>
          <div className="collapsed-summary-bar">
            <span className="summary-pill">{tripLabel}</span>
            <span className="summary-pill">{dateLabel}</span>
            <span className="summary-pill">{cabinLabel}</span>
            <span className="summary-pill">{stopLabel}</span>
            <span className="summary-pill">{currencyLabel}</span>
          </div>

          <div className="quick-edit-bar">
            <label className="quick-field">
              <span>出發</span>
              <input
                type="date"
                value={form.departure_date}
                onChange={handleTextChange("departure_date")}
              />
            </label>

            <label className="quick-field">
              <span>回程</span>
              <input
                type="date"
                value={form.return_date ?? ""}
                onChange={(event) =>
                  onChange("return_date", event.target.value || null)
                }
                disabled={form.trip_type === "one_way"}
              />
            </label>

            <label className="quick-field">
              <span>行程</span>
              <select value={form.trip_type} onChange={handleTextChange("trip_type")}>
                <option value="one_way">單程</option>
                <option value="round_trip">來回</option>
              </select>
            </label>

            <label className="quick-field">
              <span>艙等</span>
              <select value={form.cabin_class} onChange={handleTextChange("cabin_class")}>
                <option value="economy">經濟艙</option>
                <option value="business">商務艙</option>
              </select>
            </label>

            <label className="quick-field">
              <span>轉機</span>
              <select
                value={form.max_stops === null ? "unlimited" : String(form.max_stops)}
                onChange={(event) => {
                  const value = event.target.value;
                  onChange(
                    "max_stops",
                    value === "unlimited" ? null : (Number(value) as 0 | 1),
                  );
                }}
              >
                <option value="unlimited">不限</option>
                <option value="0">直飛</option>
                <option value="1">最多 1 次</option>
              </select>
            </label>

            <button
              className="quick-search-button"
              type="button"
              onClick={onQuickSearch}
              disabled={loading}
            >
              {loading ? "更新中..." : "更新結果"}
            </button>
          </div>
        </>
      ) : null}

      {!collapsed ? (
      <div className="field-grid">
        <label className="field">
          <span>出發城市</span>
          <div className="autocomplete-wrapper">
            <input
              value={form.origin_city}
              onChange={handleTextChange("origin_city")}
              onBlur={() => {
                window.setTimeout(() => setOriginSuggestions([]), 120);
              }}
              placeholder="例如：武漢 / Wuhan / HND"
              required
            />
            {renderSuggestions("origin_city", originSuggestions)}
          </div>
          <small className="field-hint">可輸入城市、機場名稱或 IATA code</small>
        </label>

        <label className="field">
          <span>目的城市</span>
          <div className="autocomplete-wrapper">
            <input
              value={form.destination_city}
              onChange={handleTextChange("destination_city")}
              onBlur={() => {
                window.setTimeout(() => setDestinationSuggestions([]), 120);
              }}
              placeholder="例如：台北 / Taipei / CDG"
              required
            />
            {renderSuggestions("destination_city", destinationSuggestions)}
          </div>
          <small className="field-hint">支援全球城市與機場查詢</small>
        </label>

        <label className="field">
          <span>出發日期</span>
          <input
            type="date"
            value={form.departure_date}
            onChange={handleTextChange("departure_date")}
            required
          />
        </label>

        <label className="field">
          <span>回程日期</span>
          <input
            type="date"
            value={form.return_date ?? ""}
            onChange={(event) =>
              onChange("return_date", event.target.value || null)
            }
            disabled={form.trip_type === "one_way"}
          />
        </label>

        <label className="field">
          <span>行程類型</span>
          <select
            value={form.trip_type}
            onChange={handleTextChange("trip_type")}
          >
            <option value="one_way">單程</option>
            <option value="round_trip">來回</option>
          </select>
        </label>

        <label className="field">
          <span>艙等</span>
          <select
            value={form.cabin_class}
            onChange={handleTextChange("cabin_class")}
          >
            <option value="economy">經濟艙</option>
            <option value="business">商務艙</option>
          </select>
        </label>

        <label className="field">
          <span>顯示幣別</span>
          <select
            value={form.currency_mode}
            onChange={handleTextChange("currency_mode")}
          >
            <option value="destination">目的地貨幣</option>
            <option value="origin">出發地貨幣</option>
            <option value="custom">指定幣別</option>
          </select>
        </label>

        {form.currency_mode === "custom" ? (
          <label className="field">
            <span>指定幣別</span>
            <input
              value={form.currency ?? ""}
              onChange={handleTextChange("currency")}
              placeholder="例如：USD"
              maxLength={3}
              required
            />
          </label>
        ) : null}

        <label className="field">
          <span>排序方式</span>
          <select value={form.sort_mode} onChange={handleTextChange("sort_mode")}>
            <option value="cheapest">最便宜</option>
            <option value="shortest">飛行時間最短</option>
            <option value="best_value">價格 / 時間綜合</option>
          </select>
        </label>

        <label className="field">
          <span>轉機限制</span>
          <select
            value={form.max_stops === null ? "unlimited" : String(form.max_stops)}
            onChange={(event) => {
              const value = event.target.value;
              onChange(
                "max_stops",
                value === "unlimited" ? null : (Number(value) as 0 | 1),
              );
            }}
          >
            <option value="unlimited">不限</option>
            <option value="0">只看直飛</option>
            <option value="1">最多 1 次轉機</option>
          </select>
        </label>
      </div>
      ) : null}

      {!collapsed ? (
        <button className="search-button" type="submit" disabled={loading}>
          {loading ? "搜尋中..." : "搜尋最低票價"}
        </button>
      ) : null}
    </form>
  );
}
