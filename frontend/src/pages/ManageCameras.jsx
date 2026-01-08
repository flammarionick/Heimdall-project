// src/pages/ManageCameras.jsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Shield,
  Camera,
  AlertTriangle,
  Users,
  BarChart3,
  Monitor,
  Video,
  Upload,
  LogOut,
  Menu,
  X,
  Clock,
  Plus,
  Edit3,
  Trash2,
  ToggleLeft,
  ToggleRight,
  Search,
  Webcam,
  Link,
  Usb,
  MapPin,
  Locate,
  Loader2,
} from "lucide-react";

// IMPORTANT: use relative routes (Vite proxy should forward to Flask)
const API_BASE = "";

export default function ManageCameras() {
  const navigate = useNavigate();

  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState("");

  // Start with empty array - will be populated from API
  const [cameras, setCameras] = useState([]);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    name: "",
    location: "",
    camera_type: "webcam",
    stream_url: "",
    device_id: "",
    latitude: "",
    longitude: ""
  });
  const [usbDevices, setUsbDevices] = useState([]);
  const [detectingLocation, setDetectingLocation] = useState(false);

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

        // Load user's cameras from API
        const res = await fetch(`${API_BASE}/api/cameras`, {
          credentials: "include",
        });
        if (res.ok) {
          const data = await res.json();
          const cams = Array.isArray(data?.cameras) ? data.cameras : [];
          setCameras(
            cams.map((c) => ({
              id: c.id,
              name: c.name || "Webcam",
              location: c.location || "Local Device",
              is_active: Boolean(c.is_active ?? c.status ?? true),
              camera_type: c.camera_type || "webcam",
              stream_url: c.stream_url || "",
              device_id: c.device_id || "",
              latitude: c.latitude || null,
              longitude: c.longitude || null
            }))
          );
        }

        // Enumerate USB video devices
        try {
          const devices = await navigator.mediaDevices.enumerateDevices();
          const videoInputs = devices.filter(d => d.kind === "videoinput");
          setUsbDevices(videoInputs);
        } catch {
          console.log("Could not enumerate devices");
        }
      } catch (err) {
        console.error(err);
        setError("Unable to load cameras.");
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

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return cameras;
    return cameras.filter(
      (c) =>
        (c.name || "").toLowerCase().includes(q) ||
        (c.location || "").toLowerCase().includes(q)
    );
  }, [cameras, query]);

  const openCreate = () => {
    setEditing(null);
    setForm({
      name: "",
      location: "",
      camera_type: "webcam",
      stream_url: "",
      device_id: "",
      latitude: "",
      longitude: ""
    });
    setModalOpen(true);
  };

  const openEdit = (cam) => {
    setEditing(cam);
    setForm({
      name: cam.name || "",
      location: cam.location || "",
      camera_type: cam.camera_type || "webcam",
      stream_url: cam.stream_url || "",
      device_id: cam.device_id || "",
      latitude: cam.latitude || "",
      longitude: cam.longitude || ""
    });
    setModalOpen(true);
  };

  const detectLocation = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser");
      return;
    }

    setDetectingLocation(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setForm((p) => ({
          ...p,
          latitude: position.coords.latitude.toFixed(6),
          longitude: position.coords.longitude.toFixed(6)
        }));
        setDetectingLocation(false);
      },
      (error) => {
        console.error("Geolocation error:", error);
        let message = "Unable to retrieve location";
        if (error.code === 1) {
          message = "Location access denied. Please allow location access in your browser settings.";
        } else if (error.code === 2) {
          message = "Location unavailable. Please check your device's GPS.";
        } else if (error.code === 3) {
          message = "Location request timed out. Please try again.";
        }
        alert(message);
        setDetectingLocation(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
      }
    );
  };

  const saveCamera = async () => {
    const name = form.name.trim();
    const location = form.location.trim();
    const { camera_type, stream_url, device_id, latitude, longitude } = form;
    if (!name) return;

    const cameraData = {
      name,
      location,
      camera_type,
      stream_url: camera_type === "rtsp" ? stream_url : null,
      device_id: camera_type === "usb" ? device_id : null,
      latitude: latitude ? parseFloat(latitude) : null,
      longitude: longitude ? parseFloat(longitude) : null
    };

    // UI-first; API optional
    if (editing) {
      setCameras((prev) =>
        prev.map((c) =>
          c.id === editing.id ? { ...c, ...cameraData } : c
        )
      );

      try {
        await fetch(`${API_BASE}/api/cameras/${editing.id}`, {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(cameraData),
        });
      } catch {
        // ignore in dev
      }
    } else {
      const newId = Math.max(0, ...cameras.map((c) => c.id)) + 1;
      const newCam = { id: newId, ...cameraData, is_active: true };
      setCameras((prev) => [newCam, ...prev]);

      try {
        await fetch(`${API_BASE}/api/cameras`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(cameraData),
        });
      } catch {
        // ignore in dev
      }
    }

    setModalOpen(false);
  };

  const toggleActive = async (id) => {
    setCameras((prev) =>
      prev.map((c) => (c.id === id ? { ...c, is_active: !c.is_active } : c))
    );

    try {
      await fetch(`${API_BASE}/api/cameras/${id}/toggle`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // ignore
    }
  };

  const removeCamera = async (id) => {
    setCameras((prev) => prev.filter((c) => c.id !== id));
    try {
      await fetch(`${API_BASE}/api/cameras/${id}`, {
        method: "DELETE",
        credentials: "include",
      });
    } catch {
      // ignore
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading cameras…</p>
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
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-md">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-bold text-gray-800">
                Manage Cameras
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
                {me?.is_admin ? (
                  <a
                    href="/admin/dashboard"
                    className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
                  >
                    <Monitor className="w-4 h-4 mr-2 text-blue-500" />
                    Dashboard
                  </a>
                ) : (
                  <a
                    href="/dashboard"
                    className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
                  >
                    <Monitor className="w-4 h-4 mr-2 text-blue-500" />
                    Dashboard
                  </a>
                )}
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
                  className="flex items-center px-3 py-2 rounded-xl bg-blue-50"
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

        {/* Toolbar */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-5 mb-6">
          <div className="flex flex-col md:flex-row md:items-center gap-3 justify-between">
            <div className="relative w-full md:max-w-sm">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search cameras…"
                className="w-full pl-9 pr-3 py-2 rounded-xl border border-gray-200 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            </div>

            <button
              onClick={openCreate}
              className="inline-flex items-center justify-center px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold shadow hover:shadow-md transition"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Camera
            </button>
          </div>
        </div>

        {/* List */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
          <div className="p-5 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">Camera List</h2>
            <span className="text-xs px-2 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100">
              {filtered.length} shown
            </span>
          </div>

          <div className="divide-y divide-gray-100">
            {filtered.map((cam) => (
              <div key={cam.id} className="p-5 flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center">
                    {cam.camera_type === "webcam" && <Webcam className="w-5 h-5 text-blue-600" />}
                    {cam.camera_type === "rtsp" && <Link className="w-5 h-5 text-purple-600" />}
                    {cam.camera_type === "usb" && <Usb className="w-5 h-5 text-green-600" />}
                    {!cam.camera_type && <Camera className="w-5 h-5 text-blue-600" />}
                  </div>
                  <div>
                    <p className="font-semibold text-gray-800">{cam.name}</p>
                    <p className="text-sm text-gray-500">{cam.location || "—"}</p>
                    {cam.latitude && cam.longitude && (
                      <p className="text-xs text-blue-500 mt-1 flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {cam.latitude.toFixed(4)}, {cam.longitude.toFixed(4)}
                      </p>
                    )}
                    {cam.camera_type === "rtsp" && cam.stream_url && (
                      <p className="text-xs text-purple-500 mt-1 truncate max-w-xs">{cam.stream_url}</p>
                    )}
                    <div className="mt-2 flex flex-wrap gap-2">
                      <span
                        className={`text-xs px-2 py-1 rounded-full border ${
                          cam.camera_type === "webcam"
                            ? "bg-blue-50 text-blue-700 border-blue-100"
                            : cam.camera_type === "rtsp"
                            ? "bg-purple-50 text-purple-700 border-purple-100"
                            : "bg-green-50 text-green-700 border-green-100"
                        }`}
                      >
                        {cam.camera_type === "webcam" ? "Webcam" : cam.camera_type === "rtsp" ? "RTSP" : "USB"}
                      </span>
                      <span
                        className={`text-xs px-2 py-1 rounded-full border ${
                          cam.is_active
                            ? "bg-green-50 text-green-700 border-green-100"
                            : "bg-red-50 text-red-700 border-red-100"
                        }`}
                      >
                        {cam.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 sm:justify-end">
                  <button
                    onClick={() => toggleActive(cam.id)}
                    className="inline-flex items-center px-3 py-2 rounded-xl border border-gray-200 bg-gray-50 hover:bg-gray-100 transition text-sm"
                  >
                    {cam.is_active ? (
                      <>
                        <ToggleRight className="w-4 h-4 mr-2 text-green-600" />
                        Disable
                      </>
                    ) : (
                      <>
                        <ToggleLeft className="w-4 h-4 mr-2 text-red-600" />
                        Enable
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => openEdit(cam)}
                    className="inline-flex items-center px-3 py-2 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 transition text-sm"
                  >
                    <Edit3 className="w-4 h-4 mr-2 text-blue-600" />
                    Edit
                  </button>

                  <button
                    onClick={() => removeCamera(cam.id)}
                    className="inline-flex items-center px-3 py-2 rounded-xl border border-red-200 bg-red-50 hover:bg-red-100 transition text-sm text-red-700"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </button>
                </div>
              </div>
            ))}

            {!filtered.length && (
              <div className="p-10 text-center text-sm text-gray-500">
                No cameras found.
              </div>
            )}
          </div>
        </div>

        {/* Modal */}
        {modalOpen && (
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
              <div className="p-5 border-b border-gray-100 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-800">
                  {editing ? "Edit Camera" : "Add Camera"}
                </h3>
                <button
                  onClick={() => setModalOpen(false)}
                  className="w-9 h-9 rounded-xl bg-gray-50 border border-gray-200 hover:bg-gray-100 flex items-center justify-center"
                >
                  <X className="w-4 h-4 text-gray-700" />
                </button>
              </div>

              <div className="p-5 space-y-4">
                <div>
                  <label className="text-sm font-semibold text-gray-700 block mb-1">
                    Camera Name
                  </label>
                  <input
                    value={form.name}
                    onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
                    placeholder="e.g., Webcam"
                  />
                </div>

                <div>
                  <label className="text-sm font-semibold text-gray-700 block mb-1">
                    Location
                  </label>
                  <input
                    value={form.location}
                    onChange={(e) =>
                      setForm((p) => ({ ...p, location: e.target.value }))
                    }
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
                    placeholder="e.g., Local Device"
                  />
                </div>

                <div>
                  <label className="text-sm font-semibold text-gray-700 block mb-1">
                    GPS Coordinates
                  </label>
                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <input
                        value={form.latitude}
                        onChange={(e) => setForm((p) => ({ ...p, latitude: e.target.value }))}
                        className="w-full px-3 py-2 rounded-xl border border-gray-200 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300 text-sm"
                        placeholder="Latitude"
                        type="number"
                        step="any"
                      />
                    </div>
                    <div className="flex-1">
                      <input
                        value={form.longitude}
                        onChange={(e) => setForm((p) => ({ ...p, longitude: e.target.value }))}
                        className="w-full px-3 py-2 rounded-xl border border-gray-200 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300 text-sm"
                        placeholder="Longitude"
                        type="number"
                        step="any"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={detectLocation}
                      disabled={detectingLocation}
                      className="px-3 py-2 rounded-xl border border-blue-200 bg-blue-50 hover:bg-blue-100 transition text-blue-700 flex items-center gap-1 disabled:opacity-50"
                    >
                      {detectingLocation ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Locate className="w-4 h-4" />
                      )}
                      <span className="text-xs font-medium">Detect</span>
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {form.latitude && form.longitude
                      ? `Coordinates: ${form.latitude}, ${form.longitude}`
                      : "Click 'Detect' to auto-fill from your current location"}
                  </p>
                </div>

                <div>
                  <label className="text-sm font-semibold text-gray-700 block mb-2">
                    Camera Type
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setForm((p) => ({ ...p, camera_type: "webcam" }))}
                      className={`flex flex-col items-center justify-center p-3 rounded-xl border transition ${
                        form.camera_type === "webcam"
                          ? "bg-blue-50 border-blue-300 text-blue-700"
                          : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
                      }`}
                    >
                      <Webcam className="w-5 h-5 mb-1" />
                      <span className="text-xs font-medium">Webcam</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setForm((p) => ({ ...p, camera_type: "rtsp" }))}
                      className={`flex flex-col items-center justify-center p-3 rounded-xl border transition ${
                        form.camera_type === "rtsp"
                          ? "bg-purple-50 border-purple-300 text-purple-700"
                          : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
                      }`}
                    >
                      <Link className="w-5 h-5 mb-1" />
                      <span className="text-xs font-medium">RTSP</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setForm((p) => ({ ...p, camera_type: "usb" }))}
                      className={`flex flex-col items-center justify-center p-3 rounded-xl border transition ${
                        form.camera_type === "usb"
                          ? "bg-green-50 border-green-300 text-green-700"
                          : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
                      }`}
                    >
                      <Usb className="w-5 h-5 mb-1" />
                      <span className="text-xs font-medium">USB</span>
                    </button>
                  </div>
                </div>

                {form.camera_type === "rtsp" && (
                  <div>
                    <label className="text-sm font-semibold text-gray-700 block mb-1">
                      RTSP Stream URL
                    </label>
                    <input
                      value={form.stream_url}
                      onChange={(e) => setForm((p) => ({ ...p, stream_url: e.target.value }))}
                      className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-purple-300"
                      placeholder="rtsp://ip:port/stream"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Enter the RTSP URL for your IP camera or CCTV
                    </p>
                  </div>
                )}

                {form.camera_type === "usb" && (
                  <div>
                    <label className="text-sm font-semibold text-gray-700 block mb-1">
                      USB Device
                    </label>
                    <select
                      value={form.device_id}
                      onChange={(e) => setForm((p) => ({ ...p, device_id: e.target.value }))}
                      className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-green-300"
                    >
                      <option value="">Select a device</option>
                      {usbDevices.map((device, i) => (
                        <option key={device.deviceId || i} value={device.deviceId}>
                          {device.label || `Camera ${i + 1}`}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Select the USB camera device to use
                    </p>
                  </div>
                )}
              </div>

              <div className="p-5 border-t border-gray-100 flex items-center justify-end gap-2">
                <button
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 transition font-semibold text-gray-700"
                >
                  Cancel
                </button>
                <button
                  onClick={saveCamera}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold shadow hover:shadow-md transition"
                >
                  {editing ? "Save Changes" : "Create Camera"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}