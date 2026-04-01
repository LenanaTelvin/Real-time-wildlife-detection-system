/**
 * frontend/components/VideoFeed.jsx
 *
 * The live video panel (left side of the dashboard).
 *
 * The backend sends an MJPEG stream (a continuous flow of JPEG frames).
 * We connect to it by pointing an <img> src at the backend URL.
 * The backend already draws bounding boxes before sending each frame.
 *
 * Props:
 *   isRunning  {bool}    — whether camera is active
 *   onStart    {func}    — called when Start button clicked
 *   onStop     {func}    — called when Stop button clicked
 *   onUpload   {func}    — called with File when user uploads a video
 *   fps        {number}  — current FPS to display
 *   frameCount {number}  — current frame number to display
 */

import { useRef } from "react";

// ── FIX 1: BACKEND_URL now reads from environment variable ───────────────────
// Previously hardcoded to "http://localhost:5000" which only works on the
// machine running the backend. Fails on phones, other laptops, and production.
// Set VITE_API_URL in frontend/.env for local dev.
// On Render, render.yaml sets it to the deployed backend URL automatically.
const BACKEND_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5000`; // was: "http://localhost:5000" hardcoded

export default function VideoFeed({ isRunning, onStart, onStop, onUpload, fps, frameCount }) {
  const fileInputRef = useRef(null);

  function handleFileChange(e) {
    const file = e.target.files[0];
    if (file) onUpload(file);
    e.target.value = "";
  }

  return (
    <div className="panel">

      <div className="panel-header">
        <span className="panel-title">Live Video Feed</span>
        <span className="frame-counter">
          FRAME {frameCount || "—"}
        </span>
      </div>

      <div className="video-wrapper">
        {/*
          Stream connection — points to GET /api/video/stream on the backend.
          When camera is running, the backend pushes annotated frames here.
          Bounding boxes are already drawn by the backend before sending.
        */}
        {isRunning && (
          <img
            src={`${BACKEND_URL}/api/video/stream`}
            alt="Live detection feed"
            className="video-feed-img"
          />
        )}

        {!isRunning && (
          <div className="video-overlay">
            <span className="overlay-icon">📷</span>
            <span className="overlay-text">Camera inactive — press Start</span>
          </div>
        )}
      </div>

      <div className="video-controls">

        <button
          className="btn btn-primary"
          onClick={onStart}
          disabled={isRunning}
        >
          ▶ Start
        </button>

        <button
          className="btn btn-danger"
          onClick={onStop}
          disabled={!isRunning}
        >
          ■ Stop
        </button>

        <button
          className="btn btn-secondary"
          onClick={() => fileInputRef.current.click()}
        >
          ⬆ Upload Video
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />

        <span className="fps-badge">
          FPS: <strong>{fps || "—"}</strong>
        </span>
      </div>
    </div>
  );
}