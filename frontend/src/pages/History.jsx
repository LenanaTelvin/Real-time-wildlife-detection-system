/**
 * frontend/pages/History.jsx
 *
 * THE HISTORY PAGE — shows the full detection log table.
 *
 * API calls made here (UPDATED for your backend):
 *   GET    /api/ai/history?limit=100&species=<filter>
 *   DELETE /api/ai/history/<id>
 * 
 * All requests include JWT token for authentication.
 */

import { useState, useEffect } from "react";
import { useNavigate, Link} from "react-router-dom";
import { authService } from "../services/authService";
import api from "../services/api";
import DetectionOverlay from "../components/DetectionOverlay";

// Backend URL from environment variable
const BACKEND_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5000/api`;

export default function History() {
  const [logs, setLogs] = useState([]);
  const [totalCount, setTotal] = useState(0);
  const [speciesFilter, setFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // Check authentication on mount
  useEffect(() => {
    if (!authService.isAuthenticated()) {
      navigate('/login');
      return;
    }
  }, []);

  // Load logs when filter changes
  useEffect(() => {
    if (authService.isAuthenticated()) {
      loadLogs(speciesFilter);
    }
  }, [speciesFilter]);

  // Poll for updates every 10 seconds
  useEffect(() => {
    if (!authService.isAuthenticated()) return;
    
    const interval = setInterval(() => loadLogs(speciesFilter), 10000);
    return () => clearInterval(interval);
  }, [speciesFilter]);

  // ── FETCH LOGS (UPDATED for your backend) ─────────────────────────────────
  async function loadLogs(species = "") {
    setLoading(true);
    try {
      // Use your backend endpoint: /api/ai/history
      let url = '/ai/history?limit=100';
      if (species) {
        url += `&species=${species}`;
      }
      
      const response = await api.get(url);
      // Your backend returns { data: [...], count: number }
      const data = response.data.data || [];
      setLogs(data);
      setTotal(response.data.count || data.length);
    } catch (error) {
      console.error('Failed to load logs:', error);
      if (error.response?.status === 401) {
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  }

  // ── DELETE A LOG ENTRY (if your backend supports it) ──────────────────────
  async function handleDelete(id) {
    if (!window.confirm('Are you sure you want to delete this detection?')) {
      return;
    }
    
    try {
      // Try to delete using your backend endpoint
      await api.delete(`/ai/history/${id}`);
      // Refresh the list after deletion
      await loadLogs(speciesFilter);
    } catch (error) {
      console.error('Failed to delete:', error);
      if (error.response?.status === 404) {
        alert('Delete endpoint not implemented on backend yet');
      } else if (error.response?.status === 401) {
        alert('Session expired. Please login again.');
        navigate('/login');
      } else {
        alert('Failed to delete detection');
      }
    }
  }

  // ── RENDER ─────────────────────────────────────────────────────────────────
  if (loading && logs.length === 0) {
    return (
      <div className="loading-container">
        <div className="loading-spinner-large"></div>
      </div>
    );
  }

  return (
    <DetectionOverlay
      logs={logs}
      totalCount={totalCount}
      onDelete={handleDelete}
      onFilter={(val) => setFilter(val)}
    />
  );
}