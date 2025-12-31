// src/pages/LiveMonitoring.jsx
import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Shield,
  Video,
  Camera,
  AlertTriangle,
  Users,
  BarChart3,
  Monitor,
  Upload,
  LogOut,
  Menu,
  X,
  Clock,
  Search,
  Wifi,
  WifiOff,
  Webcam,
  Link,
  Usb,
  Play,
  Square,
  Scan,
  User,
} from "lucide-react";
import { io } from "socket.io-client";
import EscapedInmateAlarm from "../components/EscapedInmateAlarm";

// IMPORTANT: use relative routes (Vite proxy should forward to Flask)
const API_BASE = "";

export default function LiveMonitoring() {
  const navigate = useNavigate();

  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(null);

  // Video streaming state
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState("");

  // Facial recognition state
  const [recognizing, setRecognizing] = useState(false);
  const [recognitionResult, setRecognitionResult] = useState(null);
  const [recognitionStatus, setRecognitionStatus] = useState("");
  const recognitionIntervalRef = useRef(null);
  const [videoReady, setVideoReady] = useState(false);  // Track when video metadata is loaded

  // Escaped inmate alarm state
  const [escapedAlarm, setEscapedAlarm] = useState(null);
  const socketRef = useRef(null);

  // Basic UI-only feeds (safe fallback if API for cameras isn't ready)
  const [feeds, setFeeds] = useState([
    { id: 1, name: "Default Webcam", location: "Local Device", online: true, camera_type: "webcam" },
  ]);

  useEffect(() => {
    const init = async () => {
      try {
        const meRes = await fetch(`${API_BASE}/auth/api/me`, {
          credentials: "include",
        });

        if (meRes.status === 401) {
          navigate("/login");
          return;
        }

        const meData = await meRes.json();
        setMe(meData);

        // Load cameras from API
        try {
          const camsRes = await fetch(`${API_BASE}/api/cameras`, {
            credentials: "include",
          });
          if (camsRes.ok) {
            const camsData = await camsRes.json();
            const cams = Array.isArray(camsData?.cameras) ? camsData.cameras : [];
            if (cams.length) {
              setFeeds(
                cams.map((c) => ({
                  id: c.id,
                  name: c.name || `Camera ${c.id}`,
                  location: c.location || "Unknown",
                  online: Boolean(c.is_active ?? c.status ?? true),
                  camera_type: c.camera_type || "webcam",
                  stream_url: c.stream_url || "",
                  device_id: c.device_id || ""
                }))
              );
            }
          }
        } catch {
          // ignore - keep fallback feeds
        }
      } catch (err) {
        console.error(err);
        setError("Unable to load live monitoring.");
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate]);

  // Set up Socket.IO connection for real-time alerts
  useEffect(() => {
    // Connect to socket server
    socketRef.current = io(API_BASE || window.location.origin, {
      withCredentials: true,
      transports: ['websocket', 'polling']
    });

    // Listen for escaped inmate alarms from backend
    socketRef.current.on('escaped_inmate_alarm', (data) => {
      console.log('[LiveMonitoring] Escaped inmate alarm received:', data);
      setEscapedAlarm(data);
    });

    // Cleanup on unmount
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE}/auth/api/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // ignore
    } finally {
      window.location.href = "/login";
    }
  };

  // Stop any existing stream
  const stopStream = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsStreaming(false);
    setStreamError("");
    setVideoReady(false);  // Reset video ready state
  }, [stream]);

  // Start webcam or USB camera stream
  const startStream = useCallback(async (feed) => {
    stopStream();
    setStreamError("");

    if (!feed || !feed.online) {
      setStreamError("Camera is offline");
      return;
    }

    if (feed.camera_type === "rtsp") {
      setStreamError("RTSP streaming requires server-side proxy (not yet implemented)");
      return;
    }

    try {
      const constraints = {
        video: feed.camera_type === "usb" && feed.device_id
          ? { deviceId: { exact: feed.device_id } }
          : true,
        audio: false
      };

      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      setStream(mediaStream);
      setIsStreaming(true);

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      console.error("Failed to start stream:", err);
      if (err.name === "NotAllowedError") {
        setStreamError("Camera access denied. Please allow camera permissions.");
      } else if (err.name === "NotFoundError") {
        setStreamError("Camera not found. Please check your device.");
      } else {
        setStreamError(`Failed to start camera: ${err.message}`);
      }
    }
  }, [stopStream]);

  // Capture frame and send to recognition API
  const captureAndRecognize = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || !isStreaming || !videoReady) {
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;

    // Set canvas to video's natural dimensions (avoid distortion)
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    if (canvas.width === 0 || canvas.height === 0) {
      setRecognitionStatus("Video dimensions not ready");
      return;
    }

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    setRecognitionStatus("Analyzing frame...");

    // Convert to blob
    canvas.toBlob(async (blob) => {
      if (!blob) {
        setRecognitionStatus("Failed to capture frame");
        return;
      }

      const formData = new FormData();
      formData.append('frame', blob, 'frame.jpg');

      try {
        const res = await fetch('/api/recognition/match', {
          method: 'POST',
          credentials: 'include',
          body: formData
        });

        const data = await res.json();

        if (res.ok) {
          if (data.status === 'escaped_inmate_detected') {
            // CRITICAL: Escaped inmate detected - trigger alarm!
            setRecognitionResult(data.inmate);
            setRecognitionStatus("ESCAPED INMATE DETECTED!");
            setEscapedAlarm({
              inmate: data.inmate,
              timestamp: new Date().toISOString(),
              requires_acknowledgment: true
            });
          } else if (data.status === 'match_found') {
            setRecognitionResult(data.inmate);
            setRecognitionStatus("Match found!");
          } else if (data.status === 'no_match') {
            setRecognitionResult(null);
            setRecognitionStatus("No match - scanning...");
          } else if (data.status === 'no_face_detected') {
            setRecognitionResult(null);
            setRecognitionStatus("No face detected - position face in frame");
          } else if (data.status === 'low_confidence') {
            setRecognitionResult(null);
            setRecognitionStatus(`Low confidence (${data.confidence}%) - no reliable match`);
          } else {
            setRecognitionStatus(data.error || "Unknown response");
          }
        } else {
          // Handle HTTP errors
          setRecognitionStatus(`Error: ${data.error || res.statusText}`);
          console.error('Recognition API error:', data);
        }
      } catch (err) {
        console.error('Recognition fetch error:', err);
        setRecognitionStatus(`Network error: ${err.message}`);
      }
    }, 'image/jpeg', 0.85);
  }, [isStreaming, videoReady]);

  // Start facial recognition
  const startRecognition = useCallback(() => {
    // Check if video is ready (metadata loaded and dimensions available)
    if (!videoReady) {
      setRecognitionStatus("Waiting for video to load...");
      // Retry after 500ms
      const retryTimeout = setTimeout(() => {
        if (videoRef.current && videoRef.current.videoWidth > 0 && isStreaming) {
          setVideoReady(true);
          startRecognition();
        }
      }, 500);
      return () => clearTimeout(retryTimeout);
    }

    setRecognizing(true);
    setRecognitionStatus("Starting recognition...");
    // Capture and analyze every 2 seconds
    recognitionIntervalRef.current = setInterval(captureAndRecognize, 2000);
    // Also run immediately
    captureAndRecognize();
  }, [captureAndRecognize, videoReady, isStreaming]);

  // Stop facial recognition
  const stopRecognition = useCallback(() => {
    setRecognizing(false);
    if (recognitionIntervalRef.current) {
      clearInterval(recognitionIntervalRef.current);
      recognitionIntervalRef.current = null;
    }
    setRecognitionResult(null);
    setRecognitionStatus("");
  }, []);

  // Sync stream to video element when stream or isStreaming changes
  // This fixes the race condition where state updates before srcObject is set
  useEffect(() => {
    if (stream && videoRef.current && isStreaming) {
      videoRef.current.srcObject = stream;
    }
  }, [stream, isStreaming]);

  // Clean up stream and recognition on unmount
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
      if (recognitionIntervalRef.current) {
        clearInterval(recognitionIntervalRef.current);
      }
    };
  }, [stream]);

  const filteredFeeds = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return feeds;
    return feeds.filter(
      (f) =>
        (f.name || "").toLowerCase().includes(q) ||
        (f.location || "").toLowerCase().includes(q)
    );
  }, [feeds, query]);

  const selectedFeed =
    filteredFeeds.find((f) => f.id === selectedId) || filteredFeeds[0] || null;

  useEffect(() => {
    if (!selectedId && filteredFeeds.length) setSelectedId(filteredFeeds[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filteredFeeds.length]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading live monitoring…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 text-center">{error}</p>
        </div>
      </div>
    );
  }

  // Handler for dismissing the escaped inmate alarm
  const handleDismissAlarm = useCallback(() => {
    setEscapedAlarm(null);
    setRecognitionResult(null);
    setRecognitionStatus("Alarm acknowledged - continuing scan...");
  }, []);

  return (
    <>
      {/* Escaped Inmate Alarm Modal */}
      {escapedAlarm && (
        <EscapedInmateAlarm
          inmate={escapedAlarm.inmate}
          alertId={escapedAlarm.alert_id}
          detectionLocation={escapedAlarm.detection_location}
          timestamp={escapedAlarm.timestamp}
          onDismiss={handleDismissAlarm}
        />
      )}

      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-4 md:p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
        <header className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-md">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-bold text-gray-800">
                Live Monitoring
              </h1>
              <p className="text-xs md:text-sm text-gray-500">
                {me?.email || "Admin"}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center bg-white rounded-xl px-3 py-2 shadow">
              <Clock className="w-4 h-4 text-blue-500 mr-2" />
              <span className="text-xs md:text-sm font-medium text-gray-700">
                {new Date().toLocaleDateString("en-US", {
                  weekday: "long",
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </span>
            </div>
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white shadow-md border border-gray-100 hover:bg-gray-50 transition"
            >
              {menuOpen ? (
                <X className="w-5 h-5 text-gray-700" />
              ) : (
                <Menu className="w-5 h-5 text-gray-700" />
              )}
            </button>
          </div>
        </header>

        {/* Menu */}
        {menuOpen && (
          <div className="mb-6">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-3 sm:p-4">
              <nav className="flex flex-col sm:flex-row sm:flex-wrap gap-2 text-sm text-gray-700">
                <a
                  href={me?.is_admin ? "/admin/dashboard" : "/dashboard"}
                  className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
                >
                  <Monitor className="w-4 h-4 mr-2 text-blue-500" />
                  Dashboard
                </a>
                <a
                  href="/admin/live"
                  className="flex items-center px-3 py-2 rounded-xl bg-blue-50"
                >
                  <Video className="w-4 h-4 mr-2 text-purple-500" />
                  Live Monitoring
                </a>
                <a
                  href="/admin/upload"
                  className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
                >
                  <Upload className="w-4 h-4 mr-2 text-indigo-500" />
                  Upload Recognition
                </a>
                <a
                  href="/admin/inmates"
                  className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
                >
                  <Users className="w-4 h-4 mr-2 text-emerald-500" />
                  Inmate Profiles
                </a>
                <a
                  href="/admin/alerts"
                  className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
                >
                  <AlertTriangle className="w-4 h-4 mr-2 text-orange-500" />
                  Alerts & Logs
                </a>
                <a
                  href="/admin/analytics"
                  className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
                >
                  <BarChart3 className="w-4 h-4 mr-2 text-cyan-500" />
                  Analytics
                </a>
                <a
                  href="/admin/cameras"
                  className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
                >
                  <Camera className="w-4 h-4 mr-2 text-blue-500" />
                  Manage Cameras
                </a>
                {me?.is_admin && (
                  <a
                    href="/admin/users"
                    className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
                  >
                    <Shield className="w-4 h-4 mr-2 text-gray-700" />
                    Manage Users
                  </a>
                )}
                <button
                  onClick={handleLogout}
                  className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 sm:ml-auto text-left"
                >
                  <LogOut className="w-4 h-4 mr-2 text-red-500" />
                  Logout
                </button>
              </nav>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Feeds list */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-800">Cameras</h2>
              <span className="text-xs px-2 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100">
                {feeds.length} total
              </span>
            </div>

            <div className="relative mb-4">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search cameras…"
                className="w-full pl-9 pr-3 py-2 rounded-xl border border-gray-200 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            </div>

            <div className="space-y-2">
              {filteredFeeds.map((f) => {
                const active = selectedFeed?.id === f.id;
                return (
                  <button
                    key={f.id}
                    onClick={() => {
                      setSelectedId(f.id);
                      stopStream();
                    }}
                    className={`w-full text-left p-3 rounded-xl border transition ${
                      active
                        ? "bg-blue-50 border-blue-100"
                        : "bg-white border-gray-100 hover:bg-gray-50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                          {f.camera_type === "webcam" && <Webcam className="w-4 h-4 text-blue-600" />}
                          {f.camera_type === "rtsp" && <Link className="w-4 h-4 text-purple-600" />}
                          {f.camera_type === "usb" && <Usb className="w-4 h-4 text-green-600" />}
                          {!f.camera_type && <Camera className="w-4 h-4 text-gray-600" />}
                        </div>
                        <div>
                          <p className="font-semibold text-gray-800">{f.name}</p>
                          <p className="text-xs text-gray-500">{f.location}</p>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full border ${
                            f.camera_type === "webcam"
                              ? "bg-blue-50 text-blue-700 border-blue-100"
                              : f.camera_type === "rtsp"
                              ? "bg-purple-50 text-purple-700 border-purple-100"
                              : "bg-green-50 text-green-700 border-green-100"
                          }`}
                        >
                          {f.camera_type === "webcam" ? "Webcam" : f.camera_type === "rtsp" ? "RTSP" : "USB"}
                        </span>
                        {f.online ? (
                          <span className="inline-flex items-center text-xs font-medium text-green-700">
                            <Wifi className="w-3 h-3 mr-1" /> Online
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-xs font-medium text-red-700">
                            <WifiOff className="w-3 h-3 mr-1" /> Offline
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}

              {!filteredFeeds.length && (
                <div className="text-center text-sm text-gray-500 py-10">
                  No cameras match your search.
                </div>
              )}
            </div>
          </div>

          {/* Right: Selected feed */}
          <div className="lg:col-span-2 bg-white rounded-2xl shadow-lg border border-gray-100 p-5">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center">
                  {selectedFeed?.camera_type === "webcam" && <Webcam className="w-5 h-5 text-blue-600" />}
                  {selectedFeed?.camera_type === "rtsp" && <Link className="w-5 h-5 text-purple-600" />}
                  {selectedFeed?.camera_type === "usb" && <Usb className="w-5 h-5 text-green-600" />}
                  {!selectedFeed?.camera_type && <Camera className="w-5 h-5 text-gray-600" />}
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-800">
                    {selectedFeed ? selectedFeed.name : "No camera selected"}
                  </h2>
                  <p className="text-sm text-gray-500">
                    {selectedFeed ? selectedFeed.location : ""}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {selectedFeed && (
                  <>
                    <span
                      className={`text-xs px-2 py-1 rounded-full border ${
                        selectedFeed.camera_type === "webcam"
                          ? "bg-blue-50 text-blue-700 border-blue-100"
                          : selectedFeed.camera_type === "rtsp"
                          ? "bg-purple-50 text-purple-700 border-purple-100"
                          : "bg-green-50 text-green-700 border-green-100"
                      }`}
                    >
                      {selectedFeed.camera_type === "webcam" ? "Webcam" : selectedFeed.camera_type === "rtsp" ? "RTSP" : "USB"}
                    </span>
                    <span
                      className={`text-xs px-2 py-1 rounded-full border ${
                        isStreaming
                          ? "bg-green-50 text-green-700 border-green-100"
                          : selectedFeed.online
                          ? "bg-yellow-50 text-yellow-700 border-yellow-100"
                          : "bg-red-50 text-red-700 border-red-100"
                      }`}
                    >
                      {isStreaming ? "Streaming" : selectedFeed.online ? "Ready" : "Offline"}
                    </span>
                  </>
                )}
              </div>
            </div>

            <div className="rounded-2xl overflow-hidden border border-gray-100 bg-gradient-to-br from-gray-900 to-gray-700 aspect-video flex items-center justify-center relative">
              {/* Hidden canvas for frame capture */}
              <canvas ref={canvasRef} style={{ display: 'none' }} />

              {/* Recognition result overlay */}
              {recognitionResult && (
                <div className="absolute top-4 right-4 bg-red-500/95 text-white p-4 rounded-xl shadow-lg z-10 max-w-xs">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                      {recognitionResult.mugshot_path ? (
                        <img
                          src={recognitionResult.mugshot_path}
                          alt={recognitionResult.name}
                          className="w-full h-full rounded-full object-cover"
                        />
                      ) : (
                        <User className="w-6 h-6 text-white" />
                      )}
                    </div>
                    <div>
                      <h4 className="font-bold text-lg">MATCH FOUND!</h4>
                      <p className="text-sm opacity-90">{recognitionResult.name}</p>
                    </div>
                  </div>
                  <div className="text-sm space-y-1 border-t border-white/20 pt-2 mt-2">
                    <p><span className="opacity-70">ID:</span> {recognitionResult.inmate_id}</p>
                    {recognitionResult.status && (
                      <p><span className="opacity-70">Status:</span> {recognitionResult.status}</p>
                    )}
                    {recognitionResult.risk_level && (
                      <p><span className="opacity-70">Risk:</span> {recognitionResult.risk_level}</p>
                    )}
                  </div>
                </div>
              )}

              {/* Recognition status indicator */}
              {recognizing && recognitionStatus && !recognitionResult && (
                <div className="absolute top-4 right-4 bg-blue-500/90 text-white px-4 py-2 rounded-xl shadow-lg z-10">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-white rounded-full animate-pulse" />
                    <span className="text-sm">{recognitionStatus}</span>
                  </div>
                </div>
              )}

              {isStreaming ? (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  onLoadedMetadata={(e) => {
                    e.target.play();
                    setVideoReady(true);  // Signal that video dimensions are available
                  }}
                  className="w-full h-full object-cover"
                />
              ) : streamError ? (
                <div className="text-center px-6">
                  <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
                  <p className="text-white font-semibold">Stream Error</p>
                  <p className="text-red-300 text-sm mt-1">{streamError}</p>
                </div>
              ) : selectedFeed?.camera_type === "rtsp" ? (
                <div className="text-center px-6">
                  <Link className="w-12 h-12 text-purple-400 mx-auto mb-3" />
                  <p className="text-white font-semibold">RTSP Camera</p>
                  <p className="text-white/70 text-sm mt-1">
                    RTSP URL: {selectedFeed.stream_url || "Not configured"}
                  </p>
                  <p className="text-yellow-300 text-xs mt-2">
                    Note: RTSP streaming requires a server-side proxy
                  </p>
                </div>
              ) : (
                <div className="text-center px-6">
                  <Video className="w-12 h-12 text-white/90 mx-auto mb-3" />
                  <p className="text-white font-semibold">
                    {selectedFeed ? "Click Start to begin streaming" : "Select a camera"}
                  </p>
                  <p className="text-white/70 text-sm mt-1">
                    {selectedFeed?.camera_type === "webcam"
                      ? "Browser webcam feed"
                      : selectedFeed?.camera_type === "usb"
                      ? "USB camera device"
                      : "No camera selected"}
                  </p>
                </div>
              )}
            </div>

            {/* Stream Controls */}
            <div className="mt-4 flex items-center justify-center gap-3 flex-wrap">
              {!isStreaming ? (
                <button
                  onClick={() => startStream(selectedFeed)}
                  disabled={!selectedFeed || !selectedFeed.online}
                  className="inline-flex items-center px-6 py-3 rounded-xl bg-gradient-to-r from-green-500 to-emerald-500 text-white font-semibold shadow hover:shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Play className="w-5 h-5 mr-2" />
                  Start Stream
                </button>
              ) : (
                <>
                  <button
                    onClick={stopStream}
                    className="inline-flex items-center px-6 py-3 rounded-xl bg-gradient-to-r from-red-500 to-rose-500 text-white font-semibold shadow hover:shadow-md transition"
                  >
                    <Square className="w-5 h-5 mr-2" />
                    Stop Stream
                  </button>

                  {/* Recognition Toggle Button */}
                  {!recognizing ? (
                    <button
                      onClick={startRecognition}
                      disabled={!videoReady}
                      className={`inline-flex items-center px-6 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-semibold shadow hover:shadow-md transition ${!videoReady ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <Scan className="w-5 h-5 mr-2" />
                      {videoReady ? 'Start Recognition' : 'Loading Video...'}
                    </button>
                  ) : (
                    <button
                      onClick={stopRecognition}
                      className="inline-flex items-center px-6 py-3 rounded-xl bg-gradient-to-r from-yellow-500 to-orange-500 text-white font-semibold shadow hover:shadow-md transition"
                    >
                      <Square className="w-5 h-5 mr-2" />
                      Stop Recognition
                    </button>
                  )}
                </>
              )}
            </div>

            <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-4 rounded-2xl border border-gray-100 bg-gray-50">
                <p className="text-xs text-gray-500 mb-1">Status</p>
                <p className="font-semibold text-gray-800">
                  {isStreaming ? "Streaming" : selectedFeed?.online ? "Ready" : "Offline"}
                </p>
              </div>
              <div className="p-4 rounded-2xl border border-gray-100 bg-gray-50">
                <p className="text-xs text-gray-500 mb-1">Camera Type</p>
                <p className="font-semibold text-gray-800">
                  {selectedFeed?.camera_type === "webcam" ? "Webcam" : selectedFeed?.camera_type === "rtsp" ? "RTSP IP Camera" : selectedFeed?.camera_type === "usb" ? "USB Camera" : "—"}
                </p>
              </div>
              <div className="p-4 rounded-2xl border border-gray-100 bg-gray-50">
                <p className="text-xs text-gray-500 mb-1">Location</p>
                <p className="font-semibold text-gray-800">{selectedFeed?.location || "—"}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}