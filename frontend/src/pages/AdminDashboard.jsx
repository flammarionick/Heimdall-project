// src/pages/AdminDashboard.jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
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
  ArrowRight,
  Zap,
  Shield,
  ShieldCheck,
} from "lucide-react";

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
        const meRes = await fetch("/auth/api/me", { credentials: "include" });
        if (meRes.status === 401) { navigate("/login"); return; }
        const meData = await meRes.json();
        if (!meData.is_admin) { navigate("/dashboard"); return; }
        setMe(meData);

        const statsRes = await fetch("/admin/api/stats2", { credentials: "include" });
        if (statsRes.ok) setStats(await statsRes.json());

        const healthRes = await fetch("/api/user/health", { credentials: "include" });
        if (healthRes.ok) setHealthData(await healthRes.json());
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
    try { await fetch("/auth/api/logout", { method: "POST", credentials: "include" }); }
    catch (e) { /* ignore */ }
    finally { window.location.href = "/login"; }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md text-center border border-gray-100">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-800 mb-2">Error</h3>
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  const statusDisplay = healthData?.system_status === 'critical'
    ? { text: 'Critical', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', dot: 'bg-red-500' }
    : healthData?.system_status === 'warning'
    ? { text: 'Warning', color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200', dot: 'bg-yellow-500' }
    : { text: 'Operational', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', dot: 'bg-emerald-500' };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <img src="/logo.png" alt="Heimdall" className="w-10 h-10 object-contain" />
            <div>
              <h1 className="text-xl md:text-2xl font-bold text-gray-800">
                Admin Dashboard
              </h1>
              <p className="text-xs md:text-sm text-gray-500">{me?.email || "Welcome back"}</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center bg-white rounded-xl px-3 py-2 shadow border border-gray-100">
              <Clock className="w-4 h-4 text-blue-500 mr-2" />
              <span className="text-xs md:text-sm font-medium text-gray-700">
                {new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
              </span>
            </div>
            <button onClick={() => setMenuOpen((v) => !v)} className="p-2.5 rounded-xl bg-white shadow border border-gray-100 hover:bg-gray-50 transition">
              {menuOpen ? <X className="w-5 h-5 text-gray-700" /> : <Menu className="w-5 h-5 text-gray-700" />}
            </button>
          </div>
        </header>

        {/* Menu */}
        {menuOpen && (
          <div className="mb-6">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-3 sm:p-4">
              <nav className="flex flex-col sm:flex-row sm:flex-wrap gap-2 text-sm text-gray-700">
                <a href="/admin/dashboard" className="flex items-center px-3 py-2 rounded-xl bg-blue-50 text-blue-700">
                  <Monitor className="w-4 h-4 mr-2" />Dashboard
                </a>
                <a href="/admin/live" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Video className="w-4 h-4 mr-2 text-purple-500" />Live Monitoring
                </a>
                <a href="/admin/upload" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Upload className="w-4 h-4 mr-2 text-indigo-500" />Upload Recognition
                </a>
                <a href="/admin/inmates" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Users className="w-4 h-4 mr-2 text-emerald-500" />Inmate Profiles
                </a>
                <a href="/admin/alerts" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <AlertTriangle className="w-4 h-4 mr-2 text-orange-500" />Alerts & Logs
                </a>
                <a href="/admin/analytics" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <BarChart3 className="w-4 h-4 mr-2 text-cyan-500" />Analytics
                </a>
                <a href="/admin/cameras" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Camera className="w-4 h-4 mr-2 text-blue-500" />Manage Cameras
                </a>
                <a href="/admin/users" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Users className="w-4 h-4 mr-2 text-gray-500" />Manage Users
                </a>
                <button onClick={handleLogout} className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 sm:ml-auto text-left">
                  <LogOut className="w-4 h-4 mr-2 text-red-500" />Logout
                </button>
              </nav>
            </div>
          </div>
        )}

        {/* System Status Banner */}
        <div className={`rounded-2xl border ${statusDisplay.border} ${statusDisplay.bg} mb-6`}>
          <div className="p-5 flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-white shadow-sm border border-gray-100">
                <ShieldCheck className={`w-7 h-7 ${statusDisplay.color}`} />
              </div>
              <div>
                <p className="text-sm text-gray-500 font-medium">System Status</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className={`w-2.5 h-2.5 rounded-full ${statusDisplay.dot} animate-pulse`}></span>
                  <span className={`text-xl font-bold ${statusDisplay.color}`}>{statusDisplay.text}</span>
                </div>
              </div>
            </div>
            {healthData && (
              <div className="flex items-center gap-6 text-sm">
                <div className="text-right">
                  <p className="text-gray-500">Alert Score</p>
                  <p className="font-bold text-gray-800">{healthData.alert_score || 0}</p>
                </div>
                <div className="w-px h-10 bg-gray-200"></div>
                <div className="text-right">
                  <p className="text-gray-500">24h Alerts</p>
                  <p className="font-bold text-gray-800">{healthData.alerts_24h || 0}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          {[
            { icon: Users, title: "Total Users", value: stats?.total_users || 0, change: 12, bgColor: "bg-blue-100", color: "text-blue-600" },
            { icon: CheckCircle, title: "Active Users", value: stats?.active_users || 0, change: 8, bgColor: "bg-emerald-100", color: "text-emerald-600" },
            { icon: Camera, title: "Active Cameras", value: stats?.total_cameras || 0, change: 5, bgColor: "bg-purple-100", color: "text-purple-600" },
            { icon: AlertTriangle, title: "Total Alerts", value: stats?.total_alerts || 0, bgColor: "bg-orange-100", color: "text-orange-600" },
          ].map((stat, i) => (
            <div key={i} className="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all transform hover:scale-[1.02] border border-gray-100">
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-xl ${stat.bgColor}`}>
                  <stat.icon className={`w-6 h-6 ${stat.color}`} />
                </div>
                {stat.change && (
                  <div className="flex items-center text-sm">
                    <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                    <span className="text-green-600 font-semibold">{stat.change}%</span>
                  </div>
                )}
              </div>
              <p className="text-gray-500 text-sm font-medium mb-1">{stat.title}</p>
              <p className="text-3xl font-bold text-gray-800">{Number(stat.value).toLocaleString()}</p>
            </div>
          ))}
        </div>

        {/* System Health */}
        {healthData && (
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 mb-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-cyan-100">
                  <Zap className="w-5 h-5 text-cyan-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-800">System Health</h3>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                healthData.db_status === 'healthy' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
              }`}>
                DB: {healthData.db_status}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { label: "Camera Uptime", value: healthData.camera_uptime || 0, color: "emerald" },
                { label: "Recognition Accuracy", value: healthData.recognition_accuracy || 0, color: "cyan" },
                { label: "Response Time", value: Math.max(0, 100 - (healthData.avg_response_time || 0) * 20), suffix: `${healthData.avg_response_time || 0}s`, color: "indigo" },
                { label: "Resolution Rate", value: healthData.resolution_rate || 0, color: "purple" },
              ].map((metric, i) => (
                <div key={i} className="p-4 rounded-xl bg-gray-50 border border-gray-100">
                  <div className="flex justify-between text-sm mb-3">
                    <span className="text-gray-600 font-medium">{metric.label}</span>
                    <span className="font-bold text-gray-800">{metric.suffix || `${metric.value}%`}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className={`bg-${metric.color}-500 h-2 rounded-full transition-all`} style={{ width: `${metric.value}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-lg bg-indigo-100">
              <Zap className="w-5 h-5 text-indigo-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-800">Quick Actions</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { href: "/admin/users", icon: Users, label: "Manage Users", desc: "Add, edit, or remove users", bgColor: "bg-blue-100", color: "text-blue-600" },
              { href: "/admin/live", icon: Video, label: "Live Monitoring", desc: "View camera feeds", bgColor: "bg-purple-100", color: "text-purple-600" },
              { href: "/admin/upload", icon: Upload, label: "Upload Recognition", desc: "Analyze face images", bgColor: "bg-emerald-100", color: "text-emerald-600" },
              { href: "/admin/inmates", icon: Users, label: "Inmate Profiles", desc: "View and manage profiles", bgColor: "bg-yellow-100", color: "text-yellow-600" },
              { href: "/admin/alerts", icon: AlertTriangle, label: "Alerts & Logs", desc: "Review system alerts", bgColor: "bg-red-100", color: "text-red-600" },
              { href: "/admin/analytics", icon: BarChart3, label: "Analytics", desc: "View reports and trends", bgColor: "bg-indigo-100", color: "text-indigo-600" },
            ].map((action, i) => (
              <a key={i} href={action.href}
                className="group flex items-center p-4 rounded-xl bg-gray-50 border border-gray-100 hover:shadow-md hover:border-gray-200 transition-all">
                <div className={`p-3 rounded-xl ${action.bgColor} mr-4`}>
                  <action.icon className={`w-6 h-6 ${action.color}`} />
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-800">{action.label}</p>
                  <p className="text-xs text-gray-500">{action.desc}</p>
                </div>
                <ArrowRight className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
