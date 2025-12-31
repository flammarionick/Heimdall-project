// src/pages/AdminDashboard.jsx
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Shield,
  ShieldCheck,
  Users,
  Activity,
  AlertTriangle,
  Camera,
  LogOut,
  Menu,
  X,
  Monitor,
  Video,
  Upload,
  BarChart3,
  Clock,
  TrendingUp,
  CheckCircle,
} from "lucide-react";

// Use relative paths - Vite proxy handles routing to backend

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [stats, setStats] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        // Check authentication
        const meRes = await fetch("/auth/api/me", {
          credentials: "include",
        });

        if (meRes.status === 401) {
          navigate("/login");
          return;
        }

        const meData = await meRes.json();

        if (!meData.is_admin) {
          navigate("/dashboard");
          return;
        }

        setMe(meData);

        // Load admin stats
        const statsRes = await fetch("/admin/api/stats2", {
          credentials: "include",
        });

        if (statsRes.ok) {
          const statsData = await statsRes.json();
          setStats(statsData);
        }

        // Load health data for system status
        const healthRes = await fetch("/api/user/health", {
          credentials: "include",
        });

        if (healthRes.ok) {
          const healthJson = await healthRes.json();
          setHealthData(healthJson);
        }
      } catch (err) {
        console.error(err);
        setError("Unable to load dashboard.");
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate]);

  const handleLogout = async () => {
    try {
      await fetch("/auth/api/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch (e) {
      // ignore
    } finally {
      window.location.href = "/login";
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard…</p>
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

  // Helper to get system status display properties
  const getStatusDisplay = (status) => {
    switch (status) {
      case 'critical':
        return { text: 'Critical', color: 'text-red-600', bgColor: 'bg-red-100', dotColor: 'bg-red-500' };
      case 'warning':
        return { text: 'Warning', color: 'text-orange-600', bgColor: 'bg-orange-100', dotColor: 'bg-orange-500' };
      case 'operational':
      default:
        return { text: 'Operational', color: 'text-green-600', bgColor: 'bg-green-100', dotColor: 'bg-green-500' };
    }
  };

  const statusDisplay = getStatusDisplay(healthData?.system_status);

  const StatCard = ({ icon: Icon, title, value, change, color, bgColor }) => (
    <div className="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all transform hover:scale-[1.02] border border-gray-100">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-xl ${bgColor}`}>
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
        {change && (
          <div className="flex items-center text-sm">
            <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
            <span className="text-green-600 font-semibold">{change}%</span>
          </div>
        )}
      </div>
      <h3 className="text-gray-500 text-sm font-medium mb-1">{title}</h3>
      <p className="text-3xl font-bold text-gray-800">
        {Number(value || 0).toLocaleString()}
      </p>
    </div>
  );

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
                Heimdall Admin
              </h1>
              <p className="text-xs md:text-sm text-gray-500">
                {me?.email || "Admin Dashboard"}
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
                  href="/admin/dashboard"
                  className="flex items-center px-3 py-2 rounded-xl bg-blue-50"
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
                  <Camera className="w-4 h-4 mr-2 text-indigo-500" />
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
                  href="/admin/users"
                  className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
                >
                  <Shield className="w-4 h-4 mr-2 text-gray-700" />
                  Manage Users
                </a>
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

        {/* Main Dashboard */}
        <div className="mb-6">
          <h2 className="text-2xl md:text-3xl font-bold text-gray-800 mb-2">
            Dashboard Overview
          </h2>
          <p className="text-gray-600 flex items-center">
            <Activity className="w-4 h-4 mr-2 text-blue-500" />
            Real-time security monitoring and analytics
          </p>
        </div>

        {/* System Status Banner */}
        <div className={`rounded-2xl p-4 mb-6 shadow-lg border ${statusDisplay.bgColor} border-gray-100`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-xl bg-white/50`}>
                <ShieldCheck className={`w-6 h-6 ${statusDisplay.color}`} />
              </div>
              <div>
                <p className="text-sm text-gray-600 font-medium">System Status</p>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${statusDisplay.dotColor} animate-pulse`}></span>
                  <span className={`text-lg font-bold ${statusDisplay.color}`}>{statusDisplay.text}</span>
                </div>
              </div>
            </div>
            {healthData && (
              <div className="text-right text-sm text-gray-600">
                <p>Alert Score: <span className="font-semibold">{healthData.alert_score || 0}</span></p>
                <p>Unresolved: {healthData.alerts_24h || 0} in 24h</p>
              </div>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            icon={Users}
            title="Total Users"
            value={stats?.total_users || 0}
            change={12}
            color="text-blue-600"
            bgColor="bg-blue-100"
          />
          <StatCard
            icon={CheckCircle}
            title="Active Users"
            value={stats?.active_users || 0}
            change={8}
            color="text-green-600"
            bgColor="bg-green-100"
          />
          <StatCard
            icon={Camera}
            title="Active Cameras"
            value={stats?.total_cameras || 0}
            change={5}
            color="text-purple-600"
            bgColor="bg-purple-100"
          />
          <StatCard
            icon={AlertTriangle}
            title="Total Alerts"
            value={stats?.total_alerts || 0}
            color="text-orange-600"
            bgColor="bg-orange-100"
          />
        </div>

        {/* System Health */}
        {healthData && (
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-800">System Health</h3>
              <span className={`text-xs px-2 py-1 rounded-full ${healthData.db_status === 'healthy' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                DB: {healthData.db_status}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Camera Uptime */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Camera Uptime</span>
                  <span className="font-semibold text-gray-800">{healthData.camera_uptime || 0}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full transition-all" style={{ width: `${healthData.camera_uptime || 0}%` }}></div>
                </div>
              </div>
              {/* Recognition Accuracy */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Recognition Accuracy</span>
                  <span className="font-semibold text-gray-800">{healthData.recognition_accuracy || 0}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-gradient-to-r from-blue-500 to-cyan-500 h-2 rounded-full transition-all" style={{ width: `${healthData.recognition_accuracy || 0}%` }}></div>
                </div>
              </div>
              {/* Response Time */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Response Time</span>
                  <span className="font-semibold text-gray-800">{healthData.avg_response_time || 0}s</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all" style={{ width: `${Math.max(0, 100 - (healthData.avg_response_time || 0) * 20)}%` }}></div>
                </div>
              </div>
              {/* Resolution Rate */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Resolution Rate</span>
                  <span className="font-semibold text-gray-800">{healthData.resolution_rate || 0}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-gradient-to-r from-indigo-500 to-violet-500 h-2 rounded-full transition-all" style={{ width: `${healthData.resolution_rate || 0}%` }}></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Quick Links */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            Quick Actions
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <a
              href="/admin/users"
              className="flex items-center p-4 rounded-xl bg-gradient-to-br from-blue-50 to-cyan-50 hover:from-blue-100 hover:to-cyan-100 transition-all border border-blue-100"
            >
              <Users className="w-8 h-8 text-blue-600 mr-3" />
              <div>
                <p className="font-semibold text-gray-800">Manage Users</p>
                <p className="text-xs text-gray-600">Add, edit, or remove users</p>
              </div>
            </a>
            <a
              href="/admin/live"
              className="flex items-center p-4 rounded-xl bg-gradient-to-br from-purple-50 to-pink-50 hover:from-purple-100 hover:to-pink-100 transition-all border border-purple-100"
            >
              <Video className="w-8 h-8 text-purple-600 mr-3" />
              <div>
                <p className="font-semibold text-gray-800">Live Monitoring</p>
                <p className="text-xs text-gray-600">View camera feeds</p>
              </div>
            </a>
            <a
              href="/admin/upload"
              className="flex items-center p-4 rounded-xl bg-gradient-to-br from-green-50 to-emerald-50 hover:from-green-100 hover:to-emerald-100 transition-all border border-green-100"
            >
              <Upload className="w-8 h-8 text-green-600 mr-3" />
              <div>
                <p className="font-semibold text-gray-800">Upload Recognition</p>
                <p className="text-xs text-gray-600">Analyze face images</p>
              </div>
            </a>
            <a
              href="/admin/inmates"
              className="flex items-center p-4 rounded-xl bg-gradient-to-br from-yellow-50 to-orange-50 hover:from-yellow-100 hover:to-orange-100 transition-all border border-yellow-100"
            >
              <Users className="w-8 h-8 text-orange-600 mr-3" />
              <div>
                <p className="font-semibold text-gray-800">Inmate Profiles</p>
                <p className="text-xs text-gray-600">View and manage profiles</p>
              </div>
            </a>
            <a
              href="/admin/alerts"
              className="flex items-center p-4 rounded-xl bg-gradient-to-br from-red-50 to-pink-50 hover:from-red-100 hover:to-pink-100 transition-all border border-red-100"
            >
              <AlertTriangle className="w-8 h-8 text-red-600 mr-3" />
              <div>
                <p className="font-semibold text-gray-800">Alerts & Logs</p>
                <p className="text-xs text-gray-600">Review system alerts</p>
              </div>
            </a>
            <a
              href="/admin/analytics"
              className="flex items-center p-4 rounded-xl bg-gradient-to-br from-cyan-50 to-blue-50 hover:from-cyan-100 hover:to-blue-100 transition-all border border-cyan-100"
            >
              <BarChart3 className="w-8 h-8 text-cyan-600 mr-3" />
              <div>
                <p className="font-semibold text-gray-800">Analytics</p>
                <p className="text-xs text-gray-600">View reports and trends</p>
              </div>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}