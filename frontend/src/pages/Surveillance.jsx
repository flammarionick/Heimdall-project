// src/pages/Surveillance.jsx
import { useEffect, useMemo, useState, useRef } from "react";
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
  Film,
  Play,
  Pause,
  Calendar,
  MapPin,
  Trash2,
  Download,
  ChevronLeft,
  ChevronRight,
  Filter,
  RefreshCw,
} from "lucide-react";

const API_BASE = "";

export default function Surveillance() {
  const navigate = useNavigate();

  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  // Recordings state
  const [recordings, setRecordings] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [dates, setDates] = useState([]);
  const [totalRecordings, setTotalRecordings] = useState(0);
  const [loadingRecordings, setLoadingRecordings] = useState(false);

  // Filters
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Pagination
  const [offset, setOffset] = useState(0);
  const limit = 12;

  // Selected recording for playback
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const videoRef = useRef(null);

  // Initialize
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

        // Load cameras with recordings
        try {
          const camsRes = await fetch(`${API_BASE}/api/recordings/cameras`, {
            credentials: "include",
          });
          if (camsRes.ok) {
            const data = await camsRes.json();
            setCameras(data.cameras || []);
          }
        } catch (e) {
          console.error("Failed to load cameras:", e);
        }

        // Load recording dates
        try {
          const datesRes = await fetch(`${API_BASE}/api/recordings/dates`, {
            credentials: "include",
          });
          if (datesRes.ok) {
            const data = await datesRes.json();
            setDates(data.dates || []);
          }
        } catch (e) {
          console.error("Failed to load dates:", e);
        }
      } catch (err) {
        console.error(err);
        setError("Unable to load surveillance.");
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate]);

  // Load recordings function (extracted for reuse)
  const loadRecordings = async () => {
    setLoadingRecordings(true);
    try {
      const params = new URLSearchParams();
      if (selectedCamera) params.append("camera_id", selectedCamera);
      if (selectedDate) params.append("date", selectedDate);
      params.append("limit", limit);
      params.append("offset", offset);

      const res = await fetch(`${API_BASE}/api/recordings/?${params}`, {
        credentials: "include",
      });

      if (res.ok) {
        const data = await res.json();
        setRecordings(data.recordings || []);
        setTotalRecordings(data.total || 0);
      }
    } catch (e) {
      console.error("Failed to load recordings:", e);
    } finally {
      setLoadingRecordings(false);
    }
  };

  // Load recordings with filters
  useEffect(() => {
    if (!loading) {
      loadRecordings();
    }
  }, [selectedCamera, selectedDate, offset, loading]);

  // Auto-refresh recordings every 30 seconds
  useEffect(() => {
    if (loading) return;

    const interval = setInterval(() => {
      loadRecordings();
    }, 30000);

    return () => clearInterval(interval);
  }, [selectedCamera, selectedDate, offset, loading]);

  // Refresh dates when camera filter changes
  useEffect(() => {
    const loadDates = async () => {
      try {
        const params = new URLSearchParams();
        if (selectedCamera) params.append("camera_id", selectedCamera);

        const res = await fetch(`${API_BASE}/api/recordings/dates?${params}`, {
          credentials: "include",
        });
        if (res.ok) {
          const data = await res.json();
          setDates(data.dates || []);
        }
      } catch (e) {
        console.error("Failed to load dates:", e);
      }
    };

    if (!loading) {
      loadDates();
    }
  }, [selectedCamera, loading]);

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

  const deleteRecording = async (id) => {
    if (!confirm("Are you sure you want to delete this recording?")) return;

    try {
      const res = await fetch(`${API_BASE}/api/recordings/${id}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (res.ok) {
        setRecordings((prev) => prev.filter((r) => r.id !== id));
        if (selectedRecording?.id === id) {
          setSelectedRecording(null);
        }
      }
    } catch (e) {
      console.error("Failed to delete recording:", e);
    }
  };

  const playRecording = (recording) => {
    setSelectedRecording(recording);
    setIsPlaying(true);
  };

  const formatDuration = (seconds) => {
    if (!seconds) return "--:--";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs
      .toString()
      .padStart(2, "0")}`;
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return "--";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (isoString) => {
    if (!isoString) return "--";
    return new Date(isoString).toLocaleString();
  };

  // Filtered recordings by search query
  const filteredRecordings = useMemo(() => {
    if (!searchQuery.trim()) return recordings;
    const q = searchQuery.toLowerCase();
    return recordings.filter(
      (r) =>
        r.camera?.name?.toLowerCase().includes(q) ||
        r.location_name?.toLowerCase().includes(q) ||
        r.filename?.toLowerCase().includes(q)
    );
  }, [recordings, searchQuery]);

  const totalPages = Math.ceil(totalRecordings / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading surveillance...</p>
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-rose-600 flex items-center justify-center shadow-md">
              <Film className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-bold text-gray-800">
                Surveillance Recordings
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
                <a
                  href="/admin/surveillance"
                  className="flex items-center px-3 py-2 rounded-xl bg-rose-50"
                >
                  <Film className="w-4 h-4 mr-2 text-rose-500" />
                  Surveillance
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

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar - Filters */}
          <div className="lg:col-span-1 space-y-4">
            {/* Search */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Search className="w-4 h-4" />
                Search
              </h3>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search recordings..."
                className="w-full px-3 py-2 rounded-xl border border-gray-200 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-rose-300 text-sm"
              />
            </div>

            {/* Camera Filter */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Camera className="w-4 h-4" />
                Camera
              </h3>
              <select
                value={selectedCamera || ""}
                onChange={(e) => {
                  setSelectedCamera(e.target.value || null);
                  setOffset(0);
                }}
                className="w-full px-3 py-2 rounded-xl border border-gray-200 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-rose-300 text-sm"
              >
                <option value="">All Cameras</option>
                {cameras.map((cam) => (
                  <option key={cam.id} value={cam.id}>
                    {cam.name} ({cam.recording_count})
                  </option>
                ))}
              </select>
            </div>

            {/* Date Filter */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Date
              </h3>
              <select
                value={selectedDate || ""}
                onChange={(e) => {
                  setSelectedDate(e.target.value || null);
                  setOffset(0);
                }}
                className="w-full px-3 py-2 rounded-xl border border-gray-200 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-rose-300 text-sm"
              >
                <option value="">All Dates</option>
                {dates.map((d) => (
                  <option key={d.date} value={d.date}>
                    {d.date} ({d.count})
                  </option>
                ))}
              </select>
            </div>

            {/* Stats */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                Statistics
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Total Recordings</span>
                  <span className="font-semibold">{totalRecordings}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Cameras</span>
                  <span className="font-semibold">{cameras.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Recording Days</span>
                  <span className="font-semibold">{dates.length}</span>
                </div>
              </div>
            </div>

            {/* Clear Filters */}
            {(selectedCamera || selectedDate || searchQuery) && (
              <button
                onClick={() => {
                  setSelectedCamera(null);
                  setSelectedDate(null);
                  setSearchQuery("");
                  setOffset(0);
                }}
                className="w-full py-2 px-4 bg-gray-100 hover:bg-gray-200 rounded-xl text-sm text-gray-700 flex items-center justify-center gap-2 transition"
              >
                <RefreshCw className="w-4 h-4" />
                Clear Filters
              </button>
            )}
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-3 space-y-6">
            {/* Video Player */}
            {selectedRecording && (
              <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-800">
                      {selectedRecording.camera?.name || "Unknown Camera"}
                    </h3>
                    <p className="text-sm text-gray-500">
                      {formatDate(selectedRecording.start_time)}
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedRecording(null)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition"
                  >
                    <X className="w-5 h-5 text-gray-500" />
                  </button>
                </div>
                <div className="aspect-video bg-black relative">
                  <video
                    ref={videoRef}
                    src={`${API_BASE}/api/recordings/${selectedRecording.id}/stream`}
                    controls
                    autoPlay
                    className="w-full h-full"
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                  />
                </div>
                <div className="p-4 flex items-center justify-between text-sm text-gray-600">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {formatDuration(selectedRecording.duration)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Film className="w-4 h-4" />
                      {formatFileSize(selectedRecording.file_size)}
                    </span>
                    {selectedRecording.location_name && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-4 h-4" />
                        {selectedRecording.location_name}
                      </span>
                    )}
                  </div>
                  <a
                    href={`${API_BASE}/api/recordings/${selectedRecording.id}/stream`}
                    download={selectedRecording.filename}
                    className="flex items-center gap-1 text-blue-600 hover:text-blue-700"
                  >
                    <Download className="w-4 h-4" />
                    Download
                  </a>
                </div>
              </div>
            )}

            {/* Recordings Grid */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
              <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                  <Film className="w-5 h-5 text-rose-500" />
                  Recordings
                  {loadingRecordings && (
                    <RefreshCw className="w-4 h-4 animate-spin text-gray-400" />
                  )}
                </h3>
                <span className="text-sm text-gray-500">
                  {totalRecordings} total
                </span>
              </div>

              {filteredRecordings.length === 0 ? (
                <div className="p-12 text-center">
                  <Film className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No recordings found</p>
                  <p className="text-sm text-gray-400 mt-1">
                    {selectedCamera || selectedDate
                      ? "Try adjusting your filters"
                      : "Start recording from Live Monitoring"}
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
                  {filteredRecordings.map((recording) => (
                    <div
                      key={recording.id}
                      className={`rounded-xl border overflow-hidden cursor-pointer transition hover:shadow-md ${
                        selectedRecording?.id === recording.id
                          ? "border-rose-300 bg-rose-50"
                          : "border-gray-100 bg-gray-50"
                      }`}
                      onClick={() => playRecording(recording)}
                    >
                      <div className="aspect-video bg-gray-900 relative flex items-center justify-center">
                        <Film className="w-12 h-12 text-gray-600" />
                        <div className="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded">
                          {formatDuration(recording.duration)}
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            playRecording(recording);
                          }}
                          className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 bg-black/30 transition"
                        >
                          <Play className="w-12 h-12 text-white" />
                        </button>
                      </div>
                      <div className="p-3">
                        <p className="font-medium text-gray-800 text-sm truncate">
                          {recording.camera?.name || "Unknown Camera"}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {formatDate(recording.start_time)}
                        </p>
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-xs text-gray-400">
                            {formatFileSize(recording.file_size)}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteRecording(recording.id);
                            }}
                            className="p-1 hover:bg-red-100 rounded text-red-500 transition"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="p-4 border-t border-gray-100 flex items-center justify-between">
                  <button
                    onClick={() => setOffset(Math.max(0, offset - limit))}
                    disabled={offset === 0}
                    className="flex items-center gap-1 px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition text-sm"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Previous
                  </button>
                  <span className="text-sm text-gray-600">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() =>
                      setOffset(Math.min((totalPages - 1) * limit, offset + limit))
                    }
                    disabled={currentPage >= totalPages}
                    className="flex items-center gap-1 px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition text-sm"
                  >
                    Next
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
