/**
 * frontend/pages/History.jsx
 *
 * THE HISTORY PAGE — shows the full detection log table.
 *
 * API calls made here:
 *   GET    /api/detections/logs?limit=100&species=<filter>
 *   DELETE /api/detections/<id>
 */

import { useState, useEffect } from "react";
import DetectionOverlay from "../components/DetectionOverlay";

// ── FIX 1: BACKEND_URL now reads from environment variable ───────────────────
// Previously hardcoded to "http://localhost:5000" which only works on the
// machine running the backend. Breaks on phones and in production on Render.
// Set VITE_API_URL in frontend/.env for local dev.
// On Render, render.yaml sets VITE_API_URL to the deployed backend URL.
const BACKEND_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5000`;
export default function History() {
  const [logs, setLogs]            = useState([]);
  const [totalCount, setTotal]     = useState(0);
  const [speciesFilter, setFilter] = useState("");

  useEffect(() => {
    loadLogs(speciesFilter);
  }, [speciesFilter]);

  useEffect(() => {
    const interval = setInterval(() => loadLogs(speciesFilter), 10000);
    return () => clearInterval(interval);
  }, [speciesFilter]);


  // ── FETCH LOGS ─────────────────────────────────────────────────────────────
  async function loadLogs(species = "") {
    const url = species
      ? `${BACKEND_URL}/api/detections/logs?limit=100&species=${species}`
      : `${BACKEND_URL}/api/detections/logs?limit=100`;

    try {
      const res  = await fetch(url);
      const data = await res.json();
      setLogs(data.logs || []);
      setTotal(data.total || 0);
    } catch {
      // Backend may be offline
    }
  }


  // ── DELETE A LOG ENTRY ─────────────────────────────────────────────────────
  async function handleDelete(id) {
    try {
      await fetch(`${BACKEND_URL}/api/detections/${id}`, { method: "DELETE" });
      loadLogs(speciesFilter);
    } catch {
      alert("Could not delete — is backend running?");
    }
  }


  // ── RENDER ─────────────────────────────────────────────────────────────────
  return (
    <DetectionOverlay
      logs={logs}
      totalCount={totalCount}
      onDelete={handleDelete}
      onFilter={(val) => setFilter(val)}
    />
  );
}