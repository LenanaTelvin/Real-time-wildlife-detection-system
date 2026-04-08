// src/components/VideoFeed.jsx
import { useRef, useState, useEffect } from "react";
import api from "../services/api";

export default function VideoFeed({ isRunning, onStart, onStop, onUpload, fps, frameCount }) {
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const [sampleRate, setSampleRate] = useState(10);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [cameraError, setCameraError] = useState(null);
  const [currentAnnotatedFrame, setCurrentAnnotatedFrame] = useState(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);

  // Cleanup on unmount or when isRunning becomes false
  useEffect(() => {
    if (!isRunning) {
      // Clean up when component stops running
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    }
  }, [isRunning]);

  async function handleStartCamera() {
    console.log("🎥 Starting camera...");
    setCameraError(null);
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false
      });
      
      console.log("✅ Camera access granted");
      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          console.log("📹 Video loaded, playing...");
          videoRef.current.play().catch(e => console.error("Play error:", e));
        };
      }
      
      await api.post('/camera/start', { source: 'webcam' });
      
      // Send frames for detection
      const canvas = document.createElement('canvas');
      canvas.width = 640;
      canvas.height = 480;
      const context = canvas.getContext('2d');
      
      intervalRef.current = setInterval(async() => {
        if (videoRef.current && videoRef.current.videoWidth > 0) {
          context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
          const base64Image = canvas.toDataURL('image/jpeg', 0.7);
          try {
            const response = await api.post('/video/upload_frame', { image: base64Image });
            if (response.data.annotated_frame) {
              setCurrentAnnotatedFrame(response.data.annotated_frame);
            }

            if (response.data.detections && onDetectionUpdate) {
              onDetectionUpdate(response.data.detections);
            }
          } catch (err) {
            console.error('Frame upload error:', err);
          }
        }
      }, 100);        

      
      onStart();
      
    } catch (error) {
      console.error('Camera error:', error);
      setCameraError(error.message);
    }
  }

  async function handleStopCamera() {
    console.log("🛑 Stopping camera...");
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    
    await api.post('/camera/stop').catch(console.error);
    onStop();
  }

  function handleFileChange(e) {
    const file = e.target.files[0];
    if (file && file.type.startsWith('video/')) {
      setSelectedFile(file);
      setCameraError(null);
    } else {
      alert('Please select a valid video file');
      setSelectedFile(null);
    }
    e.target.value = "";
  }

  async function handleUpload() {
    if (!selectedFile) return;
    setUploading(true);
    try {
      await onUpload(selectedFile, sampleRate);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="video-feed-card">
      <div className="panel-header">
        <span className="panel-title">🎥 Live Video Feed</span>
        <span className="frame-counter">
          FRAME {frameCount || "—"}
        </span>
      </div>

      <div className="video-wrapper">
        {/* Show annotated image when camera is running AND we have an annotated frame */}
        {isRunning && currentAnnotatedFrame ? (
          <img 
            src={currentAnnotatedFrame}
            alt="Annotated Video Frame"
            className="video-feed-img"
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        ) : null}

        {/* Video element - always rendered */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="video-feed-img"
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
        />
        
        {/* Overlay - ONLY show when camera is NOT running */}
        {!isRunning && (
          <div className="video-overlay">
            <span className="overlay-icon">📷</span>
            <span className="overlay-text">Camera inactive — press Start</span>
          </div>
        )}
        
        {/* Error message */}
        {cameraError && (
          <div style={{ 
            position: 'absolute', 
            bottom: '10px', 
            left: '10px', 
            right: '10px', 
            color: 'red', 
            background: 'rgba(0,0,0,0.8)', 
            padding: '8px',
            borderRadius: '4px',
            fontSize: '12px',
            zIndex: 10
          }}>
            ⚠️ {cameraError}
          </div>
        )}
      </div>

      <div className="video-controls">
        <button className="btn btn-primary" onClick={handleStartCamera} disabled={isRunning}>
          ▶ Start
        </button>
        <button className="btn btn-danger" onClick={handleStopCamera} disabled={!isRunning}>
          ■ Stop
        </button>
        <span className="fps-badge">
          FPS: <strong>{fps || (isRunning ? "~10" : "—")}</strong>
        </span>
      </div>

      <div className="upload-divider">
        <span>──────── OR ────────</span>
      </div>

      <div className="upload-section">
        <div className="upload-controls">
          <label className="upload-label">📹 Upload Video File</label>
          
          <div className="file-input-wrapper">
            <button
              className="btn btn-secondary"
              onClick={() => fileInputRef.current?.click()}
              disabled={isRunning}
            >
              📁 Select Video
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              style={{ display: "none" }}
              onChange={handleFileChange}
              disabled={isRunning}
            />
            {selectedFile && (
              <span className="selected-file">
                {selectedFile.name}
              </span>
            )}
          </div>

          <div className="sample-rate-selector">
            <label>Processing Speed:</label>
            <select 
              value={sampleRate} 
              onChange={(e) => setSampleRate(Number(e.target.value))}
              disabled={isRunning}
            >
              <option value={5}>High Accuracy (Every 5 frames)</option>
              <option value={10}>Balanced (Every 10 frames)</option>
              <option value={15}>Fast (Every 15 frames)</option>
              <option value={30}>Very Fast (Every 30 frames)</option>
            </select>
            <span className="sample-hint">
              Lower = more accurate, slower
            </span>
          </div>

          <button
            className="btn btn-success"
            onClick={handleUpload}
            disabled={!selectedFile || isRunning || uploading}
          >
            {uploading ? '⏳ Processing...' : '⬆ Upload & Detect'}
          </button>
        </div>
      </div>
    </div>
  );
}