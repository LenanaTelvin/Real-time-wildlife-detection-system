/**
 * frontend/pages/Dashboard.jsx
 *
 * THE MAIN PAGE — wires VideoFeed + MetricsDisplay together.
 *
 * API calls made here:
 *   POST /api/camera/start       → startCamera()
 *   POST /api/camera/stop        → stopCamera()
 *   POST /api/ai/detect-video    → uploadVideo()
 *   GET  /api/detections/live    → pollLiveDetections() every 1.5s
 *   GET  /api/ai/stats           → loadStats() every 5s
 *   GET  /api/health             → checkHealth() every 10s
 */

import { useState, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import VideoFeed from "../components/VideoFeed";
import MetricsDisplay from "../components/MetricsDisplay";
import AIResults from '../components/AIResults';
import { authService } from "../services/authService";
import api from "../services/api";

const BACKEND_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5000/api`;

export default function Dashboard() {
  // ── STATE ──────────────────────────────────────────────────────────────────
  const [isCameraRunning, setIsCameraRunning] = useState(false);  // ← Use single state
  const [liveDetections, setLiveDets] = useState([]);
  const [stats, setStats] = useState({ total: 0, by_species: {}, today: 0 });
  const [recentDetections, setRecentDetections] = useState([]);
  const [fps, setFps] = useState(0);
  const [frameCount, setFrameCount] = useState(0);
  const [backendOnline, setBackendOnline] = useState(false);
  const [toast, setToast] = useState("");
  const [user, setUser] = useState(null);
  
  const uploadIntervalRef = useRef(null);
  const detectionIntervalRef = useRef(null);  // ← For live detection polling
  const navigate = useNavigate();

  // ── CHECK AUTH ON MOUNT ────────────────────────────────────────────────────
  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    if (!currentUser) {
      navigate('/login');
      return;
    }
    setUser(currentUser);
    checkHealth();
    loadStats();
    loadRecentDetections();
    
    // Cleanup on unmount
    return () => {
      if (uploadIntervalRef.current) {
        clearInterval(uploadIntervalRef.current);
      }
      if (detectionIntervalRef.current) {
        clearInterval(detectionIntervalRef.current);
      }
    };
  }, []);

  // ── START LIVE DETECTION POLLING WHEN CAMERA IS RUNNING ────────────────────
  useEffect(() => {
    if (isCameraRunning) {
      // Start polling for live detections
      detectionIntervalRef.current = setInterval(pollLiveDetections, 1500);
    } else {
      if (detectionIntervalRef.current) {
        clearInterval(detectionIntervalRef.current);
        detectionIntervalRef.current = null;
      }
      // Clear live detections when camera stops
      setLiveDets([]);
      setFps(0);
      setFrameCount(0);
    }
    
    return () => {
      if (detectionIntervalRef.current) {
        clearInterval(detectionIntervalRef.current);
      }
    };
  }, [isCameraRunning]);

  // ── HEALTH CHECK ───────────────────────────────────────────────────────────
  async function checkHealth() {
    try {
      const res = await fetch(`${BACKEND_URL}/health`);
      setBackendOnline(res.ok);
    } catch {
      setBackendOnline(false);
    }
  }

  // ── START CAMERA ───────────────────────────────────────────────────────────
  async function startCamera() {
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

    try {
      // Call backend to start camera processing
      const response = await fetch(`${BACKEND_URL}/camera/start`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ 
          source: "webcam",
          facingMode: isMobile ? "environment" : "user"
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to start camera on backend");
      }

      // Get local camera stream
      const constraints = {
        video: {
          facingMode: isMobile ? { exact: "environment" } : "user",
          width: { ideal: 640 },
          height: { ideal: 480 },
        },
        audio: false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      showToast(isMobile ? "📱 Back Camera Active" : "💻 Webcam Active");

      const video = document.createElement("video");
      video.srcObject = stream;
      await video.play();

      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");

      setIsCameraRunning(true);

      // Send frames to backend for processing
      uploadIntervalRef.current = setInterval(() => {
        if (!video.videoWidth) return;

        canvas.width = 640;
        canvas.height = 480;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        const base64Image = canvas.toDataURL("image/jpeg", 0.3);

        fetch(`${BACKEND_URL}/video/upload_frame`, {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({ image: base64Image }),
        }).catch(err => console.error('Frame upload error:', err));
      }, 100);

    } catch (err) {
      console.error("Camera Error:", err);
      showToast("Camera access denied. Please check permissions.");
    }
  }

  // ── STOP CAMERA ────────────────────────────────────────────────────────────
  async function stopCamera() {
    // Stop sending frames
    if (uploadIntervalRef.current) {
      clearInterval(uploadIntervalRef.current);
      uploadIntervalRef.current = null;
    }

    // Notify backend
    try {
      await fetch(`${BACKEND_URL}/camera/stop`, { 
        method: "POST",
        headers: {
          "Authorization": `Bearer ${localStorage.getItem('token')}`
        }
      });
    } catch (error) {
      console.error("Stop camera error:", error);
    }
    
    setIsCameraRunning(false);
    showToast("Camera stopped");
  }

  // ── UPLOAD VIDEO ───────────────────────────────────────────────────────────
  async function uploadVideo(file, sampleRate = 10) {
    const formData = new FormData();
    formData.append("video", file);
    formData.append("sample_rate", sampleRate);
    
    showToast(`📤 Uploading ${file.name}...`);
    
    try {
      const response = await api.post('/ai/detect-video', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      if (response.data.success) {
        showToast(`✅ Detection complete! Primary: ${response.data.detection_summary?.primary_species || 'animals'}`);
        loadStats();
        loadRecentDetections();
      }
    } catch (error) {
      console.error("Upload error:", error);
      showToast(error.response?.data?.error || "Upload failed");
    }
  }

  // ── POLL LIVE DETECTIONS ───────────────────────────────────────────────────
  async function pollLiveDetections() {
    if (!isCameraRunning) return;
    
    try {
      const response = await api.get('/detections/live');
      setLiveDets(response.data.detections || []);
      setFps(response.data.fps || 0);
      setFrameCount(response.data.frame_count || 0);
    } catch (error) {
      console.error('Failed to get live detections:', error);
    }
  }

  // ── LOAD STATS ─────────────────────────────────────────────────────────────
  async function loadStats() {
    try {
      const response = await api.get('/ai/stats');
      setStats(response.data.statistics || { total: 0, by_species: {}, today: 0 });
    } catch (error) {
      console.error("Failed to load stats:", error);
    }
  }

  // ── LOAD RECENT DETECTIONS ─────────────────────────────────────────────────
  async function loadRecentDetections() {
    try {
      const response = await api.get('/ai/history?limit=10');
      setRecentDetections(response.data.data || []);
    } catch (error) {
      console.error('Failed to load detections:', error);
    }
  }

  // ── NAVIGATE TO HISTORY PAGE ───────────────────────────────────────────────
  const handleViewAllHistory = () => {
    navigate('/history');
  };

  // ── LOGOUT ─────────────────────────────────────────────────────────────────
  const handleLogout = () => {
    if (isCameraRunning) {
      stopCamera();
    }
    authService.logout();
    navigate('/login');
  };

  // ── TOAST HELPER ───────────────────────────────────────────────────────────
  function showToast(msg) {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  }

  // ── RENDER ─────────────────────────────────────────────────────────────────
  return (
    <div className="dashboard-container">
      <header className="dashboard-navbar">
        <div className="navbar-content">
          <div className="navbar-logo">
            <span>🦁</span>
            <h1>WILDLIFE DETECTION SYSTEM</h1>
          </div>
          <div className="navbar-user">
            <div className="status-badge">
              <div className={`status-dot ${backendOnline ? "online" : ""}`} />
              <span>{backendOnline ? "Backend Online" : "Backend Offline"}</span>
            </div>
            <span className="user-email">👤 {user?.name || user?.email}</span>
            <button onClick={handleLogout} className="logout-button">
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="dashboard-main">
        <div className="dashboard-two-column">
          <VideoFeed
            isRunning={isCameraRunning}
            onStart={startCamera}
            onStop={stopCamera}
            onUpload={uploadVideo}
            fps={fps}
            frameCount={frameCount}
          />
          <MetricsDisplay
            liveDetections={liveDetections}
            stats={stats}
            fps={fps}
            frameCount={frameCount}
          />
        </div>

        {/* Bottom Grid: AI Results */}
        <div className="bottom-grid">
          <AIResults 
            recentDetections={recentDetections} 
            onViewAll={handleViewAllHistory}
          />
        </div>
      </main>

      {/* Live Video Stream */}
      {isCameraRunning && (
        <div className="video-stream-container">
          <h3>🎥 Live Video Feed</h3>
          <img 
            src={`${BACKEND_URL.replace('/api', '')}/api/video/stream?t=${Date.now()}`}
            alt="Live Video Stream"
            className="video-stream"
          />
        </div>
      )}

      {toast && <div className="toast show">{toast}</div>}
    </div>
  );
}