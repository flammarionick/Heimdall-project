// src/pages/UploadRecognition.jsx
import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";

// CSS for police light animations
const alarmStyles = `
@keyframes flash-red {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.8; }
}
@keyframes flash-blue {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 0.3; }
}
@keyframes scan {
  0% { top: -5%; }
  100% { top: 105%; }
}
@keyframes pulse-border {
  0%, 100% { box-shadow: 0 0 20px rgba(239, 68, 68, 0.5); }
  50% { box-shadow: 0 0 60px rgba(239, 68, 68, 0.8); }
}
.animate-flash-red {
  animation: flash-red 0.5s ease-in-out infinite;
}
.animate-flash-blue {
  animation: flash-blue 0.5s ease-in-out infinite;
}
.animate-scan {
  animation: scan 2s linear infinite;
}
.animate-pulse-border {
  animation: pulse-border 1s ease-in-out infinite;
}
`;
import {
  Shield,
  Upload,
  Image as ImageIcon,
  AlertTriangle,
  Users,
  BarChart3,
  Monitor,
  Video,
  Camera,
  LogOut,
  Menu,
  X,
  Clock,
  CheckCircle,
  Loader2,
  Volume2,
  VolumeX,
} from "lucide-react";

// IMPORTANT: use relative routes (Vite proxy should forward to Flask)
const API_BASE = "";

// Police siren sound generator using Web Audio API
const createSirenSound = () => {
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const oscillator = audioCtx.createOscillator();
  const gainNode = audioCtx.createGain();

  oscillator.connect(gainNode);
  gainNode.connect(audioCtx.destination);

  oscillator.type = 'sine';
  gainNode.gain.value = 0.3;

  // Siren effect - oscillate between frequencies
  let freq = 600;
  let direction = 1;

  const sirenInterval = setInterval(() => {
    freq += direction * 20;
    if (freq >= 1000) direction = -1;
    if (freq <= 600) direction = 1;
    oscillator.frequency.setValueAtTime(freq, audioCtx.currentTime);
  }, 50);

  oscillator.start();

  return {
    stop: () => {
      clearInterval(sirenInterval);
      gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.1);
      setTimeout(() => {
        oscillator.stop();
        audioCtx.close();
      }, 100);
    }
  };
};

export default function UploadRecognition() {
  const navigate = useNavigate();

  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [menuOpen, setMenuOpen] = useState(false);

  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  // Siren/alarm state
  const [sirenActive, setSirenActive] = useState(false);
  const [sirenMuted, setSirenMuted] = useState(false);
  const [showAlarmOverlay, setShowAlarmOverlay] = useState(false);
  const sirenRef = useRef(null);

  // Start siren when escaped inmate detected
  useEffect(() => {
    if (result?.status === "escaped_inmate_detected") {
      setShowAlarmOverlay(true);
      if (!sirenMuted) {
        try {
          sirenRef.current = createSirenSound();
          setSirenActive(true);
        } catch (e) {
          console.error("Audio not supported:", e);
        }
      }
    }
    return () => {
      if (sirenRef.current) {
        sirenRef.current.stop();
        sirenRef.current = null;
        setSirenActive(false);
      }
    };
  }, [result?.status]);

  const stopSiren = useCallback(() => {
    if (sirenRef.current) {
      sirenRef.current.stop();
      sirenRef.current = null;
      setSirenActive(false);
    }
  }, []);

  const toggleMute = useCallback(() => {
    if (sirenActive) {
      stopSiren();
    }
    setSirenMuted(m => !m);
  }, [sirenActive, stopSiren]);

  const acknowledgeAlarm = useCallback(() => {
    stopSiren();
    setShowAlarmOverlay(false);
  }, [stopSiren]);

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
      } catch (err) {
        console.error(err);
        setError("Unable to load upload page.");
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate]);

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

  const onPickFile = () => fileRef.current?.click();

  const onFileChange = (f) => {
    setResult(null);
    setError("");
    setFile(f || null);

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (f) setPreviewUrl(URL.createObjectURL(f));
    else setPreviewUrl("");
  };

  const canSubmit = useMemo(() => Boolean(file) && !submitting, [file, submitting]);

  const submit = async () => {
    if (!file) return;

    setSubmitting(true);
    setResult(null);
    setError("");

    try {
      const form = new FormData();
      form.append("file", file);

      // If your backend route differs, adjust this endpoint ONLY.
      // Keep it relative.
      const res = await fetch(`${API_BASE}/api/recognition/upload`, {
        method: "POST",
        credentials: "include",
        body: form,
      });

      const data = await res.json().catch(() => ({}));

      if (res.status === 401) {
        navigate("/login");
        return;
      }

      if (!res.ok) {
        setError(data?.error || "Recognition failed. Please try again.");
        return;
      }

      setResult(data);
    } catch (err) {
      console.error(err);
      setError("Unable to reach server. Ensure Flask is running.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading upload page…</p>
        </div>
      </div>
    );
  }

  if (error && !file && !result) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 text-center">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Inject alarm animation styles */}
      <style>{alarmStyles}</style>

      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-4 md:p-6">
      {/* ESCAPED INMATE ALARM OVERLAY */}
      {showAlarmOverlay && result?.status === "escaped_inmate_detected" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Animated background - police lights effect */}
          <div className="absolute inset-0 overflow-hidden">
            <div className="absolute inset-0 bg-black/80" />
            <div className="absolute inset-0 animate-pulse-fast">
              <div className="absolute top-0 left-0 w-1/2 h-full bg-gradient-to-r from-red-600/40 to-transparent animate-flash-red" />
              <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-blue-600/40 to-transparent animate-flash-blue" />
            </div>
            {/* Scanning line effect */}
            <div className="absolute inset-0 overflow-hidden">
              <div className="absolute w-full h-1 bg-gradient-to-r from-transparent via-red-500 to-transparent animate-scan" />
            </div>
          </div>

          {/* Alarm content */}
          <div className="relative z-10 w-full max-w-2xl mx-4">
            {/* Top alert bar */}
            <div className="flex items-center justify-center gap-3 mb-6 animate-pulse">
              <div className="w-4 h-4 rounded-full bg-red-500 animate-ping" />
              <span className="text-red-500 text-sm font-bold tracking-widest uppercase">
                Security Alert Active
              </span>
              <div className="w-4 h-4 rounded-full bg-red-500 animate-ping" />
            </div>

            {/* Main alert card */}
            <div className="bg-gradient-to-b from-gray-900 to-gray-800 rounded-3xl border-2 border-red-500/50 shadow-2xl shadow-red-500/20 overflow-hidden">
              {/* Header with siren icon */}
              <div className="bg-gradient-to-r from-red-600 via-red-500 to-red-600 px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center animate-pulse">
                    <AlertTriangle className="w-7 h-7 text-white" />
                  </div>
                  <div>
                    <h2 className="text-white text-xl md:text-2xl font-black tracking-tight">
                      ESCAPED INMATE DETECTED
                    </h2>
                    <p className="text-red-100 text-sm">Immediate action required</p>
                  </div>
                </div>
                <button
                  onClick={toggleMute}
                  className="p-3 rounded-full bg-white/20 hover:bg-white/30 transition"
                  title={sirenMuted ? "Unmute alarm" : "Mute alarm"}
                >
                  {sirenMuted ? (
                    <VolumeX className="w-6 h-6 text-white" />
                  ) : (
                    <Volume2 className="w-6 h-6 text-white animate-pulse" />
                  )}
                </button>
              </div>

              {/* Inmate details */}
              <div className="p-6">
                <div className="flex flex-col md:flex-row gap-6">
                  {/* Mugshot */}
                  <div className="flex-shrink-0 mx-auto md:mx-0">
                    <div className="relative">
                      <div className="absolute -inset-1 bg-gradient-to-r from-red-500 to-orange-500 rounded-2xl blur opacity-75 animate-pulse" />
                      <div className="relative w-32 h-32 md:w-40 md:h-40 rounded-2xl overflow-hidden border-4 border-red-500 bg-gray-700">
                        {result.inmate?.mugshot_path ? (
                          <img
                            src={result.inmate.mugshot_path}
                            alt={result.inmate.name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <Users className="w-16 h-16 text-gray-500" />
                          </div>
                        )}
                      </div>
                      <div className="absolute -bottom-2 -right-2 w-8 h-8 rounded-full bg-red-500 flex items-center justify-center animate-bounce">
                        <AlertTriangle className="w-5 h-5 text-white" />
                      </div>
                    </div>
                  </div>

                  {/* Details grid */}
                  <div className="flex-1 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-gray-700/50 rounded-xl p-3">
                        <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">Name</p>
                        <p className="text-white font-bold text-lg">{result.inmate?.name || "Unknown"}</p>
                      </div>
                      <div className="bg-gray-700/50 rounded-xl p-3">
                        <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">Inmate ID</p>
                        <p className="text-white font-mono font-bold">{result.inmate?.inmate_id || "N/A"}</p>
                      </div>
                      <div className="bg-red-900/50 rounded-xl p-3 border border-red-500/30">
                        <p className="text-red-300 text-xs uppercase tracking-wide mb-1">Status</p>
                        <p className="text-red-400 font-black text-lg flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                          ESCAPED
                        </p>
                      </div>
                      <div className="bg-gray-700/50 rounded-xl p-3">
                        <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">Risk Level</p>
                        <p className={`font-bold text-lg ${
                          result.inmate?.risk_level === "High" ? "text-red-400" :
                          result.inmate?.risk_level === "Medium" ? "text-yellow-400" : "text-green-400"
                        }`}>
                          {result.inmate?.risk_level || "Unknown"}
                        </p>
                      </div>
                    </div>

                    {/* Confidence meter */}
                    <div className="bg-gray-700/50 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-gray-400 text-xs uppercase tracking-wide">Match Confidence</p>
                        <p className="text-white font-bold">{result.inmate?.confidence || 0}%</p>
                      </div>
                      <div className="h-3 bg-gray-600 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 rounded-full transition-all duration-500"
                          style={{ width: `${result.inmate?.confidence || 0}%` }}
                        />
                      </div>
                    </div>

                    {result.inmate?.crime && (
                      <div className="bg-gray-700/50 rounded-xl p-3">
                        <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">Crime</p>
                        <p className="text-white">{result.inmate.crime}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Action buttons */}
                <div className="mt-6 flex flex-col sm:flex-row gap-3">
                  <button
                    onClick={acknowledgeAlarm}
                    className="flex-1 px-6 py-4 bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 text-white font-bold rounded-xl shadow-lg shadow-red-500/30 transition-all flex items-center justify-center gap-2"
                  >
                    <CheckCircle className="w-5 h-5" />
                    Acknowledge Alert
                  </button>
                  <button
                    onClick={() => {
                      acknowledgeAlarm();
                      navigate("/admin/inmates");
                    }}
                    className="flex-1 px-6 py-4 bg-gray-700 hover:bg-gray-600 text-white font-bold rounded-xl transition-all flex items-center justify-center gap-2"
                  >
                    <Users className="w-5 h-5" />
                    View Inmate Profile
                  </button>
                </div>
              </div>
            </div>

            {/* Timestamp */}
            <div className="mt-4 text-center">
              <p className="text-gray-400 text-sm">
                Detected at {new Date().toLocaleTimeString()} • {new Date().toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-md">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-bold text-gray-800">
                Upload Recognition
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
                  className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
                >
                  <Video className="w-4 h-4 mr-2 text-purple-500" />
                  Live Monitoring
                </a>
                <a
                  href="/admin/upload"
                  className="flex items-center px-3 py-2 rounded-xl bg-blue-50"
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

        {/* Body */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Upload card */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-2">
              Upload an image
            </h2>
            <p className="text-sm text-gray-600 mb-5">
              Upload a face image to run recognition and return the most likely match.
            </p>

            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-100 rounded-2xl">
                <div className="flex items-start">
                  <AlertTriangle className="w-5 h-5 text-red-600 mr-2 mt-0.5" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            )}

            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => onFileChange(e.target.files?.[0])}
            />

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={onPickFile}
                className="inline-flex items-center justify-center px-4 py-3 rounded-xl border border-gray-200 bg-gray-50 hover:bg-gray-100 transition font-semibold text-gray-700"
              >
                <ImageIcon className="w-4 h-4 mr-2 text-blue-600" />
                Choose Image
              </button>

              <button
                onClick={submit}
                disabled={!canSubmit}
                className="inline-flex items-center justify-center px-4 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold shadow hover:shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Analyzing…
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Run Recognition
                  </>
                )}
              </button>
            </div>

            {file && (
              <div className="mt-4 text-sm text-gray-600">
                Selected: <span className="font-semibold">{file.name}</span>
              </div>
            )}

            <div className="mt-6 p-4 rounded-2xl bg-blue-50 border border-blue-100">
              <p className="text-sm text-blue-900 font-semibold mb-1">
                Endpoint used
              </p>
              <p className="text-xs text-blue-800">
                POST <span className="font-mono">/api/recognition/upload</span>{" "}
                (adjust this only if your Flask route differs)
              </p>
            </div>
          </div>

          {/* Preview + Results */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-2">
              Preview & Results
            </h2>
            <p className="text-sm text-gray-600 mb-5">
              Review the uploaded image and recognition response.
            </p>

            <div className="rounded-2xl border border-gray-100 bg-gray-50 overflow-hidden aspect-video flex items-center justify-center">
              {previewUrl ? (
                <img
                  src={previewUrl}
                  alt="preview"
                  className="max-w-full max-h-full object-contain"
                />
              ) : (
                <div className="text-center px-6">
                  <ImageIcon className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                  <p className="text-gray-600 font-semibold">No image selected</p>
                  <p className="text-gray-500 text-sm mt-1">
                    Choose an image to see a preview here.
                  </p>
                </div>
              )}
            </div>

            <div className="mt-5">
              {!result ? (
                <div className="p-4 rounded-2xl border border-gray-100 bg-white">
                  <p className="text-sm text-gray-600">
                    Results will appear here after you run recognition.
                  </p>
                </div>
              ) : result.status === "escaped_inmate_detected" ? (
                <div className="rounded-2xl border-2 border-red-400 bg-gradient-to-br from-red-50 to-red-100 overflow-hidden animate-pulse-border">
                  {/* Alert header */}
                  <div className="bg-gradient-to-r from-red-600 to-red-500 px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-white animate-pulse" />
                      <span className="text-white font-bold text-sm tracking-wide">ESCAPED INMATE DETECTED</span>
                    </div>
                    <button
                      onClick={() => setShowAlarmOverlay(true)}
                      className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded-lg text-white text-xs font-semibold transition"
                    >
                      View Alert
                    </button>
                  </div>

                  {/* Content */}
                  <div className="p-4">
                    <div className="flex gap-4">
                      {/* Mugshot */}
                      <div className="flex-shrink-0">
                        <div className="w-20 h-20 rounded-xl overflow-hidden border-2 border-red-300 bg-gray-200">
                          {result.inmate?.mugshot_path ? (
                            <img
                              src={result.inmate.mugshot_path}
                              alt={result.inmate.name}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <Users className="w-8 h-8 text-gray-400" />
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Details */}
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-red-900 text-lg truncate">{result.inmate?.name}</p>
                        <p className="text-red-700 text-sm font-mono">{result.inmate?.inmate_id}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-red-200 text-red-800 text-xs font-bold">
                            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />
                            ESCAPED
                          </span>
                          <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            result.inmate?.risk_level === "High" ? "bg-red-200 text-red-800" :
                            result.inmate?.risk_level === "Medium" ? "bg-yellow-200 text-yellow-800" :
                            "bg-green-200 text-green-800"
                          }`}>
                            {result.inmate?.risk_level} Risk
                          </span>
                          <span className="px-2 py-1 rounded-full bg-gray-200 text-gray-700 text-xs font-semibold">
                            {result.inmate?.confidence}% Match
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : result.status === "match_found" ? (
                <div className="rounded-2xl border border-green-200 bg-gradient-to-br from-green-50 to-emerald-50 overflow-hidden">
                  {/* Success header */}
                  <div className="bg-gradient-to-r from-green-600 to-emerald-500 px-4 py-3 flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-white" />
                    <span className="text-white font-bold text-sm tracking-wide">MATCH FOUND</span>
                  </div>

                  {/* Content */}
                  <div className="p-4">
                    <div className="flex gap-4">
                      {/* Mugshot */}
                      <div className="flex-shrink-0">
                        <div className="w-20 h-20 rounded-xl overflow-hidden border-2 border-green-300 bg-gray-200">
                          {result.inmate?.mugshot_path ? (
                            <img
                              src={result.inmate.mugshot_path}
                              alt={result.inmate.name}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <Users className="w-8 h-8 text-gray-400" />
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Details */}
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-green-900 text-lg truncate">{result.inmate?.name}</p>
                        <p className="text-green-700 text-sm font-mono">{result.inmate?.inmate_id}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            result.inmate?.status === "Incarcerated" ? "bg-blue-200 text-blue-800" :
                            result.inmate?.status === "Released" ? "bg-gray-200 text-gray-800" :
                            "bg-red-200 text-red-800"
                          }`}>
                            {result.inmate?.status}
                          </span>
                          <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            result.inmate?.risk_level === "High" ? "bg-red-200 text-red-800" :
                            result.inmate?.risk_level === "Medium" ? "bg-yellow-200 text-yellow-800" :
                            "bg-green-200 text-green-800"
                          }`}>
                            {result.inmate?.risk_level} Risk
                          </span>
                          <span className="px-2 py-1 rounded-full bg-green-200 text-green-800 text-xs font-semibold">
                            {result.inmate?.confidence}% Match
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : result.status === "no_match" ? (
                <div className="p-5 rounded-2xl border border-yellow-100 bg-yellow-50">
                  <div className="flex items-start">
                    <AlertTriangle className="w-6 h-6 text-yellow-600 mr-2 mt-0.5" />
                    <div className="flex-1">
                      <p className="font-semibold text-yellow-900">
                        No Match Found
                      </p>
                      <p className="text-sm text-yellow-800 mt-1">
                        The face was detected but did not match any inmate in the database.
                      </p>
                      {/* Debug info */}
                      {result.debug_message && (
                        <div className="mt-3 p-3 bg-white rounded-xl border border-yellow-200 text-xs">
                          <p className="font-semibold text-gray-700 mb-2">Diagnostic Info:</p>
                          <p className="text-gray-600">{result.debug_message}</p>
                          <p className="text-gray-600 mt-1">
                            Compared against: {result.num_inmates_compared} inmates
                          </p>
                          <p className="text-gray-600">
                            Feature dimensions: {result.input_feature_dim}
                          </p>
                          {result.top_3_matches && result.top_3_matches.length > 0 && (
                            <div className="mt-2">
                              <p className="font-semibold text-gray-700">Top 3 closest matches:</p>
                              {result.top_3_matches.map((m, i) => (
                                <p key={i} className="text-gray-600 ml-2">
                                  {i + 1}. {m.inmate_id}: distance = {m.distance}
                                </p>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : result.status === "no_face_detected" ? (
                <div className="p-5 rounded-2xl border border-orange-100 bg-orange-50">
                  <div className="flex items-start">
                    <AlertTriangle className="w-6 h-6 text-orange-600 mr-2 mt-0.5" />
                    <div>
                      <p className="font-semibold text-orange-900">
                        No Face Detected
                      </p>
                      <p className="text-sm text-orange-800 mt-1">
                        {result.error || "Please upload an image with a clearly visible face."}
                      </p>
                    </div>
                  </div>
                </div>
              ) : result.status === "low_confidence" ? (
                <div className="p-5 rounded-2xl border border-blue-100 bg-blue-50">
                  <div className="flex items-start">
                    <AlertTriangle className="w-6 h-6 text-blue-600 mr-2 mt-0.5" />
                    <div>
                      <p className="font-semibold text-blue-900">
                        Low Confidence Match
                      </p>
                      <p className="text-sm text-blue-800 mt-1">
                        {result.message || `Confidence: ${result.confidence}% - Below threshold for reliable match`}
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-5 rounded-2xl border border-gray-100 bg-gray-50">
                  <div className="flex items-start">
                    <CheckCircle className="w-6 h-6 text-gray-600 mr-2 mt-0.5" />
                    <div>
                      <p className="font-semibold text-gray-900">
                        Recognition completed
                      </p>
                      <pre className="mt-3 text-xs bg-white border border-gray-100 rounded-xl p-3 overflow-auto">
{JSON.stringify(result, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 text-xs text-gray-500">
              Tip: If you see 401s here, your session cookie is not being stored/sent.
              Keep all API calls relative and ensure Vite proxy forwards to Flask.
            </div>
          </div>
        </div>
      </div>
    </div>
    </>
  );
}