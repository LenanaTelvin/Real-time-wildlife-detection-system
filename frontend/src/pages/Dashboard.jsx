/**
 * frontend/pages/Dashboard.jsx
 *
 * THE MAIN PAGE — wires VideoFeed + MetricsDisplay together.
 *
 * API calls made here:
 *   POST /api/camera/start       → startCamera()
 *   POST /api/camera/stop        → stopCamera()
 *   POST /api/video/upload       → uploadVideo()
 *   GET  /api/detections/live    → pollLiveDetections() every 1.5s
 *   GET  /api/detections/stats   → loadStats() every 5s
 *   GET  /api/health             → checkHealth() every 10s
 */

import { useState, useEffect, useRef } from "react";
import VideoFeed from "../components/VideoFeed";
import MetricsDisplay from "../components/MetricsDisplay";

// ── FIX 1: BACKEND_URL now reads from environment variable ───────────────────
// Previously hardcoded to "http://192.168.0.100:5000" (partner's local IP)
// which breaks for everyone else and in production.
// Create frontend/.env with: VITE_API_URL=http://localhost:5000
// On Render, render.yaml sets VITE_API_URL automatically.
const BACKEND_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5000`;

export default function Dashboard() {
  // ── STATE ──────────────────────────────────────────────────────────────────
  const [isRunning, setIsRunning]         = useState(false);
  const [liveDetections, setLiveDets]     = useState([]);
  const [stats, setStats]                 = useState({});
  const [fps, setFps]                     = useState(null);
  const [frameCount, setFrameCount]       = useState(0);
  const [backendOnline, setBackendOnline] = useState(false);
  const [toast, setToast]                 = useState("");

  // ── FIX 2: uploadInterval moved to useRef ────────────────────────────────
  // Previously declared as "let uploadInterval = null" inside the component
  // body but outside functions — not React-safe. useRef persists across
  // renders without triggering re-renders and is the correct React pattern
  // for storing mutable values like interval IDs.
  const uploadIntervalRef = useRef(null);   // was: let uploadInterval = null


  // ── POLLING INTERVALS ──────────────────────────────────────────────────────
  useEffect(() => {
    checkHealth();
    loadStats();

    const liveInterval   = setInterval(pollLiveDetections, 1500);
    const statsInterval  = setInterval(loadStats, 5000);
    const healthInterval = setInterval(checkHealth, 10000);

    return () => {
      clearInterval(liveInterval);
      clearInterval(statsInterval);
      clearInterval(healthInterval);
    };
  }, [isRunning]);


  // ── HEALTH CHECK ───────────────────────────────────────────────────────────
  async function checkHealth() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`);
      await res.json();
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }


  // ── START CAMERA ───────────────────────────────────────────────────────────
  async function startCamera() {
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

    const constraints = {
      video: {
        facingMode: isMobile ? { exact: "environment" } : "user",
        width:  { ideal: 640 },
        height: { ideal: 480 },
      },
      audio: false,
    };

    try {
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      showToast(isMobile ? "Mobile CCTV Active (Back Camera)" : "Laptop CCTV Active (Front Camera)");

      const video = document.createElement("video");
      video.srcObject = stream;
      await video.play();

      const canvas  = document.createElement("canvas");
      const context = canvas.getContext("2d");

      setIsRunning(true);

      // ── FIX 3: Interval stored in uploadIntervalRef.current ──────────────
      // Previously stored in a plain "let" variable which is not React-safe.
      uploadIntervalRef.current = setInterval(() => {   // was: uploadInterval = setInterval(...)
        if (!video.videoWidth) return;

        canvas.width  = 640;
        canvas.height = 480;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        const base64Image = canvas.toDataURL("image/jpeg", 0.3);

        fetch(`${BACKEND_URL}/api/video/upload_frame`, {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify({ image: base64Image }),
        });
      }, 100);

    } catch (err) {
      console.error("Camera Error:", err);
      showToast("Camera access denied. Use HTTPS.");
    }
  }


  // ── STOP CAMERA ────────────────────────────────────────────────────────────
  async function stopCamera() {
    // ── FIX 4: Clear the upload interval when stopping ───────────────────────
    // Previously stopCamera() never cleared uploadIntervalRef, so the phone
    // kept sending frames to the backend every 200ms forever after clicking
    // Stop — wasting bandwidth and triggering detections with no stream active.
    if (uploadIntervalRef.current) {
      clearInterval(uploadIntervalRef.current);   // was: missing entirely
      uploadIntervalRef.current = null;
    }

    try {
      await fetch(`${BACKEND_URL}/api/camera/stop`, { method: "POST" });
      setIsRunning(false);
      setLiveDets([]);
      setFps(null);
      showToast("Camera stopped");
    } catch {
      showToast("Error stopping camera");
    }
  }


  // ── UPLOAD VIDEO ───────────────────────────────────────────────────────────
  async function uploadVideo(file) {
    const formData = new FormData();
    formData.append("video", file);
    showToast(`Uploading ${file.name}...`);
    try {
      const res  = await fetch(`${BACKEND_URL}/api/video/upload`, {
        method: "POST",
        body:   formData,
      });
      const data = await res.json();
      if (data.status === "processing") {
        setIsRunning(true);
        showToast(`Processing: ${data.filename}`);
      }
    } catch {
      showToast("Upload failed");
    }
  }


  // ── POLL LIVE DETECTIONS ───────────────────────────────────────────────────
  async function pollLiveDetections() {
    if (!isRunning) return;
    try {
      const res  = await fetch(`${BACKEND_URL}/api/detections/live`);
      const data = await res.json();
      setLiveDets(data.detections || []);
      setFps(data.fps);
      setFrameCount(data.frame_count);
    } catch {
      // Silently fail
    }
  }


  // ── LOAD STATS ─────────────────────────────────────────────────────────────
  async function loadStats() {
    try {
      const res  = await fetch(`${BACKEND_URL}/api/detections/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      // Silently fail if backend offline
    }
  }


  // ── TOAST HELPER ───────────────────────────────────────────────────────────
  function showToast(msg) {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  }


  // ── RENDER ─────────────────────────────────────────────────────────────────
  return (
    <div className="dashboard">

      <header className="app-header">
        <div className="brand">
          <div className={`brand-dot ${backendOnline ? "online" : ""}`} />
          <h1>WILDLIFE DETECTION SYSTEM</h1>
        </div>
        <div className="status-badge">
          <div className={`status-dot ${backendOnline ? "online" : ""}`} />
          <span>{backendOnline ? "Backend · Online" : "Backend · Offline"}</span>
        </div>
      </header>

      <main className="main-content">
        <div className="top-grid">
          <VideoFeed
            isRunning={isRunning}
            onStart={startCamera}
            onStop={stopCamera}
            onUpload={uploadVideo}
            fps={fps}
            frameCount={frameCount}
          />
          <MetricsDisplay
            liveDetections={liveDetections}
            stats={stats}
          />
        </div>
      </main>

      {toast && <div className="toast show">{toast}</div>}
    </div>
  );
}