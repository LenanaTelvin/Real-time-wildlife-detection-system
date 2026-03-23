/**
 * frontend/pages/Dashboard.jsx
 *
 * THE MAIN PAGE — wires VideoFeed + MetricsDisplay together.
 *
 * ⭐ THIS IS WHERE ALL API CALLS HAPPEN ⭐
 * All fetch() calls to the backend are in this file.
 * Components (VideoFeed, MetricsDisplay) just receive data as props.
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

// ⭐ BACKEND URL — change this if your partner'ss backend is on another machine
const BACKEND_URL = "http://192.168.0.100:5000";

export default function Dashboard() {
  // ── STATE ──────────────────────────────────────────────────────────────────
  const [isRunning, setIsRunning]         = useState(false);
  const [liveDetections, setLiveDets]     = useState([]);
  const [stats, setStats]                 = useState({});
  const [fps, setFps]                     = useState(null);
  const [frameCount, setFrameCount]       = useState(0);
  const [backendOnline, setBackendOnline] = useState(false);
  const [toast, setToast]                 = useState("");

  // ── POLLING INTERVALS ──────────────────────────────────────────────────────
  useEffect(() => {
    checkHealth();
    loadStats();

    const liveInterval  = setInterval(pollLiveDetections, 1500);
    const statsInterval = setInterval(loadStats, 5000);
    const healthInterval = setInterval(checkHealth, 10000);

    return () => {
      clearInterval(liveInterval);
      clearInterval(statsInterval);
      clearInterval(healthInterval);
    };
  }, [isRunning]);


  // ── HEALTH CHECK ───────────────────────────────────────────────────────────
  // Calls GET /api/health to check if backend is up
  async function checkHealth() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`);
      const data = await res.json();
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }


 // ── START CAMERA ───────────────────────────────────────────────────────────
let uploadInterval = null; 

async function startCamera() {
  // 1. Detect device type
  const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
  
  // 2. Set camera: 'environment' (back) for mobile, 'user' (front) for laptop
  const constraints = {
    video: {
      facingMode: isMobile ? { exact: "environment" } : "user",
      width: { ideal: 640 },
      height: { ideal: 480 }
    },
    audio: false
  };

  try {
    // 3. Open the camera IN THE BROWSER
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    
    // 4. Show toast based on device
    showToast(isMobile ? "Mobile CCTV Active (Back Camera)" : "Laptop CCTV Active (Front Camera)");

    const video = document.createElement('video');
    video.srcObject = stream;
    await video.play();

    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');

    // 5. Send frames to Railway every 200ms
    setIsRunning(true);
    uploadInterval = setInterval(() => {
      if (!video.videoWidth) return;

      canvas.width = 640;
      canvas.height = 480;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      const base64Image = canvas.toDataURL('image/jpeg', 0.5); 

      // This sends the frame to the Railway backend
      fetch(`${BACKEND_URL}/api/video/upload_frame`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: base64Image }),
      });
    }, 200);

  } catch (err) {
    console.error("Camera Error:", err);
    showToast("⚠️ Camera access denied. Use HTTPS.");
  }
}

  // ── STOP CAMERA ────────────────────────────────────────────────────────────
  // Calls POST /api/camera/stop
  async function stopCamera() {
    try {
      await fetch(`${BACKEND_URL}/api/camera/stop`, { method: "POST" });
      setIsRunning(false);
      setLiveDets([]);
      setFps(null);
      showToast("Camera stopped");
    } catch {
      showToast("⚠️ Error stopping camera");
    }
  }


  // ── UPLOAD VIDEO ───────────────────────────────────────────────────────────
  // Calls POST /api/video/upload (multipart)
  async function uploadVideo(file) {
    const formData = new FormData();
    formData.append("video", file);
    showToast(`Uploading ${file.name}...`);
    try {
      const res = await fetch(`${BACKEND_URL}/api/video/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.status === "processing") {
        setIsRunning(true);
        showToast(`Processing: ${data.filename}`);
      }
    } catch {
      showToast("⚠️ Upload failed");
    }
  }


  // ── POLL LIVE DETECTIONS ───────────────────────────────────────────────────
  // Calls GET /api/detections/live — runs every 1.5s while camera is active
  async function pollLiveDetections() {
    if (!isRunning) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/detections/live`);
      const data = await res.json();
      setLiveDets(data.detections || []);
      setFps(data.fps);
      setFrameCount(data.frame_count);
    } catch {
      // Silently fail
    }
  }


  // ── LOAD STATS ─────────────────────────────────────────────────────────────
  // Calls GET /api/detections/stats — runs every 5s
  async function loadStats() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/detections/stats`);
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

      {/* Header */}
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
        {/* Top grid: video (left) + stats (right) */}
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

      {/* Toast notification */}
      {toast && <div className="toast show">{toast}</div>}
    </div>
  );
}
