import type { FlightOffer } from "../lib/types";

interface ResultCardProps {
  offer: FlightOffer;
  rank: number;
}

function formatDuration(totalMinutes: number): string {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours}h ${minutes}m`;
}

function formatTripPattern(offer: FlightOffer): string {
  if (offer.trip_type === "one_way") {
    return offer.direct ? "直飛" : `${offer.total_stops} 次轉機`;
  }

  const [outboundSegment, returnSegment] = offer.segments;
  if (!outboundSegment || !returnSegment) {
    return offer.direct ? "全程直飛" : `${offer.total_stops} 次轉機`;
  }

  const outboundLabel =
    outboundSegment.stops === 0 ? "去程直飛" : `去程 ${outboundSegment.stops} 次轉機`;
  const returnLabel =
    returnSegment.stops === 0 ? "回程直飛" : `回程 ${returnSegment.stops} 次轉機`;
  return `${outboundLabel} / ${returnLabel}`;
}

export function ResultCard({ offer, rank }: ResultCardProps) {
  return (
    <article className="result-card">
      <div className="card-topline">
        <span className="rank-chip">#{rank}</span>
        {offer.is_best_price ? <span className="best-price-badge">Best Price</span> : null}
        <span className="provider-chip">{offer.provider}</span>
      </div>

      <div className="price-row">
        <div>
          <p className="price-label">總價格</p>
          <p className="price-value">
            {offer.display_currency} {offer.display_price?.toLocaleString()}
          </p>
        </div>
        <div className="route-pill">
          {offer.origin_airport} → {offer.destination_airport}
        </div>
      </div>

      <div className="meta-grid">
        <div>
          <p className="meta-label">航空公司</p>
          <p>{offer.airline}</p>
        </div>
        <div>
          <p className="meta-label">航班型態</p>
          <p>{formatTripPattern(offer)}</p>
        </div>
        <div>
          <p className="meta-label">總飛行時間</p>
          <p>{formatDuration(offer.total_duration_minutes)}</p>
        </div>
        <div>
          <p className="meta-label">艙等</p>
          <p>{offer.cabin_class === "economy" ? "經濟艙" : "商務艙"}</p>
        </div>
      </div>

      <div className="segments">
        {offer.segments.map((segment) => (
          <div
            className="segment-card"
            key={`${offer.airline}-${segment.direction}-${segment.origin_airport}-${segment.destination_airport}-${segment.departure_time}`}
          >
            <p className="meta-label">
              {segment.direction === "outbound" ? "去程" : "回程"}
            </p>
            <p className="segment-time">
              {segment.origin_airport} → {segment.destination_airport}
            </p>
            <p className="segment-detail">{segment.airline}</p>
            <p className="segment-time">
              {segment.departure_time} → {segment.arrival_time}
            </p>
            <p className="segment-detail">
              {formatDuration(segment.duration_minutes)} /{" "}
              {segment.stops === 0 ? "直飛" : `${segment.stops} 次轉機`}
            </p>
          </div>
        ))}
      </div>

      <div className="card-footer">
        <div>
          <p className="meta-label">原始票價</p>
          <p>
            {offer.original_currency} {offer.original_price.toLocaleString()}
          </p>
        </div>
        {offer.purchase_link ? (
          <a
            className="book-link"
            href={offer.purchase_link}
            target="_blank"
            rel="noreferrer"
          >
            前往購買
          </a>
        ) : (
          <span className="book-link disabled">暫無連結</span>
        )}
      </div>
    </article>
  );
}
