// src/pages/UserDashboard.jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  Eye,
  Bell,
  Camera,
  TrendingUp,
  Clock,
  Shield,
  LogOut,
  AlertTriangle,
  Users,
  Menu,
  X,
  Video,
  BarChart3,
  Upload,
  ArrowRight,
  Zap,
  ShieldCheck
} from 'lucide-react';

export default function UserDashboard() {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [stats, setStats] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        const meRes = await fetch("/auth/api/me", {
          credentials: 'include'
        });

        if (meRes.status === 401) {
          navigate('/login');
          return;
        }

        const meData = await meRes.json();

        if (meData.is_admin) {
          navigate('/admin/dashboard');
          return;
        }

        setMe(meData);

        const [statsRes, activityRes, healthRes] = await Promise.all([
          fetch("/api/user/stats", { credentials: 'include' }),
          fetch("/api/user/activity", { credentials: 'include' }),
          fetch("/api/user/health", { credentials: 'include' })
        ]);

        if (statsRes.ok) {
          const statsData = await statsRes.json();
          setStats({
            todayMatches: statsData.today_matches || 0,
            activeAlerts: statsData.active_alerts || 0,
            activeCameras: statsData.active_cameras || 0,
            totalCameras: statsData.total_cameras || 0,
            totalInmates: statsData.total_inmates || 0,
            systemStatus: statsData.system_status || 'operational',
            cameraUptime: statsData.camera_uptime || 0
          });
        }

        if (activityRes.ok) {
          const activityData = await activityRes.json();
          setRecentActivity(activityData.activity || []);
        }

        if (healthRes.ok) {
          const healthData = await healthRes.json();
          setHealth({
            cameraUptime: healthData.camera_uptime || 0,
            recognitionAccuracy: healthData.recognition_accuracy || 0,
            avgResponseTime: healthData.avg_response_time || 0,
            resolutionRate: healthData.resolution_rate || 0,
            alerts24h: healthData.alerts_24h || 0,
            matches24h: healthData.matches_24h || 0,
            dbStatus: healthData.db_status || 'unknown'
          });
        }

      } catch (err) {
        console.error('Dashboard initialization error:', err);
        setError('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate]);

  const handleLogout = async () => {
    try {
      await fetch("/auth/api/logout", {
        method: 'POST',
        credentials: 'include'
      });
    } catch (e) {
      // ignore
    } finally {
      window.location.href = '/login';
    }
  };

  const getSystemStatusDisplay = (status) => {
    switch (status) {
      case 'critical':
        return { text: 'Critical', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', dot: 'bg-red-500' };
      case 'warning':
        return { text: 'Warning', color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200', dot: 'bg-yellow-500' };
      default:
        return { text: 'Operational', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', dot: 'bg-emerald-500' };
    }
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
          <p className="text-red-600 mb-6">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl text-white font-semibold hover:shadow-lg transition-all"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const systemStatusInfo = getSystemStatusDisplay(stats?.systemStatus);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <img src="/logo.png" alt="Heimdall" className="w-10 h-10 object-contain" />
            <div>
              <h1 className="text-xl md:text-2xl font-bold text-gray-800">Dashboard</h1>
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
                <a href="/dashboard" className="flex items-center px-3 py-2 rounded-xl bg-blue-50 text-blue-700">
                  <Activity className="w-4 h-4 mr-2" />Dashboard
                </a>
                <a href="/admin/live" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Video className="w-4 h-4 mr-2 text-purple-500" />Live Monitoring
                </a>
                <a href="/admin/upload" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Camera className="w-4 h-4 mr-2 text-indigo-500" />Upload Recognition
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
                <button onClick={handleLogout} className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 sm:ml-auto text-left">
                  <LogOut className="w-4 h-4 mr-2 text-red-500" />Logout
                </button>
              </nav>
            </div>
          </div>
        )}

        {/* Welcome Section */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-5 h-5 text-blue-600" />
            <span className="text-sm font-medium text-blue-600">Welcome back</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-bold text-gray-800">
            {me?.username || me?.email || 'User'}
          </h2>
          <p className="text-gray-500 mt-1">Here's your security overview for today</p>
        </div>

        {/* System Status Banner */}
        <div className={`rounded-2xl border ${systemStatusInfo.border} ${systemStatusInfo.bg} mb-6`}>
          <div className="p-5 flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-white shadow-sm border border-gray-100">
                <ShieldCheck className={`w-7 h-7 ${systemStatusInfo.color}`} />
              </div>
              <div>
                <p className="text-sm text-gray-500 font-medium">System Status</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className={`w-2.5 h-2.5 rounded-full ${systemStatusInfo.dot} animate-pulse`}></span>
                  <span className={`text-xl font-bold ${systemStatusInfo.color}`}>{systemStatusInfo.text}</span>
                </div>
              </div>
            </div>
            {health && (
              <div className="flex items-center gap-6 text-sm">
                <div className="text-right">
                  <p className="text-gray-500">24h Alerts</p>
                  <p className="font-bold text-gray-800">{health.alerts24h || 0}</p>
                </div>
                <div className="w-px h-10 bg-gray-200"></div>
                <div className="text-right">
                  <p className="text-gray-500">24h Matches</p>
                  <p className="font-bold text-gray-800">{health.matches24h || 0}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          {[
            { icon: Eye, title: "Today's Matches", value: stats?.todayMatches || 0, change: 12, bgColor: "bg-blue-100", color: "text-blue-600" },
            { icon: Bell, title: "Active Alerts", value: stats?.activeAlerts || 0, bgColor: "bg-orange-100", color: "text-orange-600" },
            { icon: Camera, title: "Active Cameras", value: `${stats?.activeCameras || 0}/${stats?.totalCameras || 0}`, change: 5, bgColor: "bg-purple-100", color: "text-purple-600" },
            { icon: Users, title: "Total Inmates", value: stats?.totalInmates || 0, bgColor: "bg-emerald-100", color: "text-emerald-600" },
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
              <p className="text-3xl font-bold text-gray-800">{typeof stat.value === 'number' ? Number(stat.value).toLocaleString() : stat.value}</p>
            </div>
          ))}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Activity */}
          <div className="lg:col-span-2 bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-100">
                  <Activity className="w-5 h-5 text-blue-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-800">Recent Activity</h3>
              </div>
              <button
                onClick={() => navigate('/admin/alerts')}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
              >
                View All
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-3">
              {recentActivity.length > 0 ? (
                recentActivity.map(activity => (
                  <div key={activity.id} className="flex items-start gap-4 p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-all border border-gray-100">
                    <div className={`p-2.5 rounded-xl ${
                      activity.level === 'danger' ? 'bg-red-100 text-red-600' :
                      activity.level === 'warning' ? 'bg-yellow-100 text-yellow-600' :
                      activity.level === 'success' ? 'bg-emerald-100 text-emerald-600' :
                      'bg-blue-100 text-blue-600'
                    }`}>
                      {activity.type === 'match' ? <Eye className="w-5 h-5" /> :
                       activity.type === 'camera' ? <Camera className="w-5 h-5" /> :
                       activity.type === 'alert' ? <Bell className="w-5 h-5" /> :
                       <Activity className="w-5 h-5" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800">{activity.message}</p>
                      <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                        <p className="text-xs text-gray-500 flex items-center">
                          <Clock className="w-3 h-3 mr-1" />
                          {activity.time}
                        </p>
                        {activity.inmate_name && (
                          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                            {activity.inmate_name}
                          </span>
                        )}
                        {activity.camera_name && (
                          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
                            {activity.camera_name}
                          </span>
                        )}
                      </div>
                    </div>
                    {activity.resolved !== undefined && (
                      <span className={`text-xs px-2 py-1 rounded-full ${activity.resolved ? 'bg-emerald-100 text-emerald-700' : 'bg-yellow-100 text-yellow-700'}`}>
                        {activity.resolved ? 'Resolved' : 'Active'}
                      </span>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center py-12">
                  <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-4">
                    <Activity className="w-8 h-8 text-gray-400" />
                  </div>
                  <p className="font-medium text-gray-600">No recent activity</p>
                  <p className="text-sm text-gray-500 mt-1">Activity will appear here as events occur</p>
                </div>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="bg-gradient-to-br from-blue-500 to-cyan-500 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-white/20">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-lg font-bold text-white">Quick Access</h3>
              </div>
              <p className="text-sm text-blue-100">Jump to frequently used features</p>
            </div>
            <div className="p-4 space-y-2">
              {[
                { href: "/admin/live", icon: Camera, label: "View Live Cameras", bgColor: "bg-purple-100", color: "text-purple-600" },
                { href: "/admin/alerts", icon: Bell, label: "Check Alerts", bgColor: "bg-orange-100", color: "text-orange-600" },
                { href: "/admin/upload", icon: Eye, label: "Upload for Recognition", bgColor: "bg-indigo-100", color: "text-indigo-600" },
                { href: "/admin/inmates", icon: Users, label: "View Inmates", bgColor: "bg-emerald-100", color: "text-emerald-600" },
              ].map((action, i) => (
                <button
                  key={i}
                  onClick={() => navigate(action.href)}
                  className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition-all text-left group"
                >
                  <div className={`p-2 rounded-lg ${action.bgColor}`}>
                    <action.icon className={`w-5 h-5 ${action.color}`} />
                  </div>
                  <span className="font-medium text-gray-700">{action.label}</span>
                  <ArrowRight className="w-4 h-4 text-gray-400 ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
