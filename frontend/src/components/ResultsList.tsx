import type { SearchResponse } from "../lib/types";
import { ResultCard } from "./ResultCard";

interface ResultsListProps {
  data: SearchResponse | null;
}

export function ResultsList({ data }: ResultsListProps) {
  if (!data) {
    return (
      <section className="results-empty">
        <p>輸入條件後按下搜尋，系統會自動展開機場並回傳排序結果。</p>
      </section>
    );
  }

  return (
    <section className="results-section" id="results-section">
      <div className="results-header">
        <div>
          <p className="results-title">最佳比價結果</p>
          <p className="results-subtitle">依目前條件排序後的可用組合</p>
        </div>
        <div className="results-count">{data.best_results.length} 筆結果</div>
      </div>
      <div className="results-summary">
        <div className="summary-card">
          <p className="meta-label">出發機場候選</p>
          <strong>{data.expanded_origin_airports.join(", ")}</strong>
        </div>
        <div className="summary-card">
          <p className="meta-label">目的地機場候選</p>
          <strong>{data.expanded_destination_airports.join(", ")}</strong>
        </div>
        <div className="summary-card">
          <p className="meta-label">結果幣別</p>
          <strong>{data.display_currency}</strong>
        </div>
        <div className="summary-card">
          <p className="meta-label">查詢組合數</p>
          <strong>{data.route_results.length}</strong>
        </div>
      </div>

      <div className="results-list">
        {data.best_results.map((offer, index) => (
          <ResultCard
            key={`${offer.origin_airport}-${offer.destination_airport}-${offer.airline}-${index}`}
            offer={offer}
            rank={index + 1}
          />
        ))}
      </div>
    </section>
  );
}
