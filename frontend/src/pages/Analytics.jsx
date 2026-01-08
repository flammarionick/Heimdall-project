import { useEffect, useMemo, useState, lazy, Suspense } from "react";
import { useNavigate } from "react-router-dom";
import {
  Shield,
  Menu,
  X,
  Monitor,
  Video,
  Camera,
  Users,
  AlertTriangle,
  BarChart3,
  LogOut,
  Clock,
  TrendingUp,
  Activity,
  Map,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

// Lazy load EscapeMap to avoid SSR issues with Leaflet
const EscapeMap = lazy(() => import("../components/EscapeMap"));

const BACKEND_BASE_URL = "";

export default function Analytics() {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const [error, setError] = useState("");

  const handleLogout = async () => {
    try {
      await fetch(`/auth/api/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch (e) {
      // ignore
    } finally {
      window.location.href = "/login";
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        const meRes = await fetch(`${BACKEND_BASE_URL}/auth/api/me`, {
          credentials: "include",
        });

        if (meRes.status === 401) {
          navigate("/login");
          return;
        }

        const meData = await meRes.json();
        setMe(meData);

        const statsRes = await fetch(`${BACKEND_BASE_URL}/admin/api/stats2`, {
          credentials: "include",
        });

        if (!statsRes.ok) {
          throw new Error("Failed to load analytics");
        }

        const statsData = await statsRes.json();
        setStats(statsData);
      } catch (err) {
        console.error(err);
        setError("Unable to load analytics.");
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate]);

  const matchesOverTime = useMemo(() => stats?.matches_over_time || [], [stats]);
  const inmateStatus = useMemo(() => stats?.inmate_status || [], [stats]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading analytics…</p>
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
              <h1 className="text-xl md:text-2xl font-bold text-gray-800">Heimdall Admin</h1>
              <p className="text-xs md:text-sm text-gray-500">{me?.email || "Analytics"}</p>
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
              {menuOpen ? <X className="w-5 h-5 text-gray-700" /> : <Menu className="w-5 h-5 text-gray-700" />}
            </button>
          </div>
        </header>

        {/* Menu */}
        {menuOpen && (
          <div className="mb-6">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-3 sm:p-4">
              <nav className="flex flex-col sm:flex-row sm:flex-wrap gap-2 text-sm text-gray-700">
                <a href={me?.is_admin ? "/admin/dashboard" : "/dashboard"} className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Monitor className="w-4 h-4 mr-2 text-blue-500" />
                  Dashboard
                </a>
                <a href="/admin/live" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Video className="w-4 h-4 mr-2 text-purple-500" />
                  Live Monitoring
                </a>
                <a href="/admin/upload" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Camera className="w-4 h-4 mr-2 text-indigo-500" />
                  Upload Recognition
                </a>
                <a href="/admin/inmates" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Users className="w-4 h-4 mr-2 text-emerald-500" />
                  Inmate Profiles
                </a>
                <a href="/admin/alerts" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <AlertTriangle className="w-4 h-4 mr-2 text-orange-500" />
                  Alerts & Logs
                </a>
                <a href="/admin/analytics" className="flex items-center px-3 py-2 rounded-xl bg-blue-50">
                  <BarChart3 className="w-4 h-4 mr-2 text-cyan-500" />
                  Analytics
                </a>
                <a href="/admin/cameras" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Camera className="w-4 h-4 mr-2 text-blue-500" />
                  Manage Cameras
                </a>
                {me?.is_admin && (
                  <a href="/admin/users" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
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

        {/* Title */}
        <div className="mb-6">
          <h2 className="text-2xl md:text-3xl font-bold text-gray-800 mb-2">Analytics</h2>
          <p className="text-gray-600 flex items-center">
            <Activity className="w-4 h-4 mr-2 text-blue-500" />
            Reports, trends, and performance metrics
          </p>
        </div>

        {/* KPI cards (same styling as dashboard) */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard icon={Users} title="Total Users" value={stats?.total_users || 0} change={12} color="text-blue-600" bgColor="bg-blue-100" />
          <StatCard icon={Activity} title="Active Users" value={stats?.active_users || 0} change={8} color="text-green-600" bgColor="bg-green-100" />
          <StatCard icon={Camera} title="Cameras" value={stats?.total_cameras || 0} change={5} color="text-purple-600" bgColor="bg-purple-100" />
          <StatCard icon={AlertTriangle} title="Total Alerts" value={stats?.total_alerts || 0} color="text-orange-600" bgColor="bg-orange-100" />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Matches over time */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Recognition Matches Over Time</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={matchesOverTime}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" strokeWidth={3} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Inmate status pie */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Inmate Status Distribution</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={inmateStatus} dataKey="value" nameKey="name" outerRadius={110} label>
                    {inmateStatus.map((_, idx) => (
                      <Cell key={idx} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Escape Locations Map */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Map className="w-5 h-5 text-red-500" />
            <h3 className="text-xl font-semibold text-gray-800">Escape Tracking</h3>
          </div>
          <Suspense fallback={
            <div className="h-[400px] bg-gray-100 rounded-xl flex items-center justify-center">
              <div className="text-center">
                <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                <p className="text-gray-600 text-sm">Loading map...</p>
              </div>
            </div>
          }>
            <EscapeMap />
          </Suspense>
        </div>
      </div>
    </div>
  );
}