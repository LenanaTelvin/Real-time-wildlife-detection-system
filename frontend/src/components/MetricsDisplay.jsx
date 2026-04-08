/**
 * frontend/components/MetricsDisplay.jsx
 *
 * The stats panel on the right side of the dashboard.
 * Shows:
 *   1. "Detecting Now" — live detections from the current frame
 *   2. Total detection count (all time)
 *   3. Per-species breakdown (lion / hyena / buffalo)
 *
 * ⭐ DATA FLOW ⭐
 * All data is passed in as props from Dashboard.jsx.
 * Dashboard.jsx fetches the data by calling:
 *   GET /api/detections/live   → liveDetections
 *   GET /api/detections/stats  → stats
 *
 * Props:
 *   liveDetections {Array}  — detections from the latest frame
 *   stats          {Object} — { total, by_species: {lion, hyena, buffalo}, today }
 */

// Species colors match bounding boxes + spec:
// Lion=green, Hyena=purple, Buffalo=red
const SPECIES_COLORS = {
  lions:    "#22c55e",
  hyenas:   "#a855f7",
  Buffalo: "#ef4444",
};

export default function MetricsDisplay({ liveDetections = [], stats = {} }) {
  const bySpecies = stats.by_species || {};

  return (
    <div className="stats-panel">

      {/* ── DETECTING NOW ─────────────────────────────────────────────── */}
      {/* Populated by polling GET /api/detections/live every 1.5s */}
      <div className="stat-card">
        <div className="stat-card-title">🔍 Detecting Now</div>
        <div className="live-detections">
          {liveDetections.length === 0 ? (
            <div className="no-detection">No detections in this frame</div>
          ) : (
            liveDetections.map((det, i) => (
              <div
                key={i}
                className={`live-det-item ${det.species}`}
                style={{ borderLeftColor: SPECIES_COLORS[det.species] || "#64748b" }}
              >
                <span className="live-det-species">{det.species}</span>
                <span className="live-det-conf">
                  {(det.confidence * 100).toFixed(1)}%
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ── TOTAL DETECTIONS ──────────────────────────────────────────── */}
      {/* Populated by polling GET /api/detections/stats every 5s */}
      <div className="stat-card">
        <div className="stat-card-title">📊 Total Detections</div>
        <div className="big-number">{stats.total ?? 0}</div>
        <div className="big-number-label">all time · {stats.today ?? 0} today</div>
      </div>
      
      {/* Card 3: Today's Detections (NEW) */}
      <div className="stat-card">
        <div className="stat-card-title">📅 Today</div>
        <div className="big-number" style={{ color: "#3b82f6" }}>
          {stats.today ?? 0}
        </div>
        <div className="big-number-label">detections today</div>
      </div>
      
      {/* ── BY SPECIES ────────────────────────────────────────────────── */}
      <div className="stat-card">
        <div className="stat-card-title">🦁 By Species</div>
        {["lions", "hyenas", "Buffalo"].map((species) => (
          <div key={species} className="species-row">
            <div className="species-indicator">
              <div
                className="species-color-dot"
                style={{ background: SPECIES_COLORS[species] }}
              />
              <span className="species-name">{species}</span>
            </div>
            <span className="species-count">{bySpecies[species] ?? 0}</span>
          </div>
        ))}
      </div>

    </div>
  );
}
