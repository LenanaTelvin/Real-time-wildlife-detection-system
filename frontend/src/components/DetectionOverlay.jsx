/**
 * frontend/components/DetectionOverlay.jsx
 *
 * The Detection History table at the bottom of the dashboard.
 *
 * Shows all logged detections with species, confidence, time, date,
 * and delete action per row.
 *
 * ⭐ DATA FLOW ⭐
 * Data is passed in as props from History.jsx.
 * History.jsx fetches data by calling:
 *   GET  /api/ai/history?limit=100&species=<filter>
 *   DELETE /api/ai/history/<id>  (when Delete is clicked)
 *
 * Props:
 *   logs       {Array}   — detection records from the database
 *   onDelete   {func}    — called with detection id when Delete clicked
 *   onFilter   {func}    — called with species string when filter changes
 *   totalCount {number}  — total entries shown in toolbar
 */

const SPECIES_COLORS = {
  lions:    "#22c55e",
  hyenas:   "#a855f7",
  buffalo:  "#ef4444",  // Changed from "Buffalo" to lowercase for consistency
};

// Helper function to format date
const formatDate = (dateString) => {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  return date.toLocaleString();
};

export default function DetectionOverlay({ logs = [], onDelete, onFilter, totalCount = 0 }) {
  return (
    <div className="logs-panel">

      {/* Toolbar: title + filter dropdown + count */}
      <div className="logs-toolbar">
        <span className="panel-title">Detection History</span>

        {/*
          Species filter — onFilter sends value to History.jsx
          which re-calls GET /api/ai/history?species=<value>
        */}
        <select
          className="filter-select"
          onChange={(e) => onFilter(e.target.value)}
          defaultValue=""
        >
          <option value="">All Species</option>
          <option value="lions">Lion</option>
          <option value="hyenas">Hyena</option>
          <option value="buffalo">Buffalo</option>
        </select>

        <span className="log-count">{totalCount} entries</span>
      </div>

      {/* Table */}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Species</th>
              <th>Confidence</th>
              <th>Date & Time</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan={4} className="table-empty">
                  No detections recorded yet
                </td>
              </tr>
            ) : (
              logs.map((log) => {
                // Get species name (handle both cases)
                const species = log.species?.toLowerCase() || '';
                const color = SPECIES_COLORS[species] || "#64748b";
                const confPct = Math.round((log.confidence || 0) * 100);
                
                return (
                  <tr key={log.id}>
                    {/* Species with color dot */}
                    <td>
                      <div className="species-tag">
                        <div className="dot" style={{ background: color }} />
                        <span style={{ color: color }}>
                          {log.species}
                        </span>
                      </div>
                    </td>

                    {/* Confidence bar + percentage */}
                    <td>
                      <div className="conf-bar-wrap">
                        <div className="conf-bar">
                          <div
                            className="conf-bar-fill"
                            style={{ width: `${confPct}%` }}
                          />
                        </div>
                        <span className="conf-text">{confPct}%</span>
                      </div>
                    </td>

                    {/* Date & Time combined */}
                    <td>
                      <span className="time-text">
                        {formatDate(log.created_at) || `${log.date} ${log.timestamp}`}
                      </span>
                    </td>

                    {/* Delete — calls DELETE /api/ai/history/<id> via onDelete prop */}
                    <td>
                      <button
                        className="action-btn"
                        onClick={() => {
                          if (window.confirm("Delete this detection record?")) {
                            onDelete(log.id);
                          }
                        }}
                      >
                        🗑 Delete
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}