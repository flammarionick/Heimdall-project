// src/pages/UserDashboard.jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Eye, Bell, Camera, TrendingUp, Clock, Shield, LogOut, AlertTriangle, Users, Menu, X, Video, BarChart3, Upload } from 'lucide-react';

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
        // Check authentication
        const meRes = await fetch("/auth/api/me", {
          credentials: 'include'
        });

        if (meRes.status === 401) {
          navigate('/login');
          return;
        }

        const meData = await meRes.json();

        // If admin, redirect to admin dashboard
        if (meData.is_admin) {
          navigate('/admin/dashboard');
          return;
        }

        setMe(meData);

        // Fetch real stats, activity, and health data in parallel
        const [statsRes, activityRes, healthRes] = await Promise.all([
          fetch("/api/user/stats", { credentials: 'include' }),
          fetch("/api/user/activity", { credentials: 'include' }),
          fetch("/api/user/health", { credentials: 'include' })
        ]);

        // Process stats
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

        // Process activity
        if (activityRes.ok) {
          const activityData = await activityRes.json();
          setRecentActivity(activityData.activity || []);
        }

        // Process health
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
        return { text: 'Critical', color: 'text-red-600', bgColor: 'bg-red-100' };
      case 'warning':
        return { text: 'Warning', color: 'text-orange-600', bgColor: 'bg-orange-100' };
      default:
        return { text: 'Operational', color: 'text-green-600', bgColor: 'bg-green-100' };
    }
  };

  const StatCard = ({ icon: Icon, title, value, subtitle, color, bgColor }) => (
    <div className="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all transform hover:scale-[1.02] border border-gray-100">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-xl ${bgColor}`}>
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
        {subtitle && (
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
            {subtitle}
          </span>
        )}
      </div>
      <h3 className="text-gray-500 text-sm font-medium mb-1">{title}</h3>
      <p className="text-3xl font-bold text-gray-800">{value}</p>
    </div>
  );

  const ActivityItem = ({ activity }) => {
    const getIcon = () => {
      switch (activity.type) {
        case 'match': return <Eye className="w-5 h-5" />;
        case 'camera': return <Camera className="w-5 h-5" />;
        case 'alert': return <Bell className="w-5 h-5" />;
        default: return <Activity className="w-5 h-5" />;
      }
    };

    const getColor = () => {
      switch (activity.level) {
        case 'danger': return 'bg-red-100 text-red-600 border-red-200';
        case 'warning': return 'bg-orange-100 text-orange-600 border-orange-200';
        case 'success': return 'bg-green-100 text-green-600 border-green-200';
        case 'info': return 'bg-blue-100 text-blue-600 border-blue-200';
        default: return 'bg-gray-100 text-gray-600 border-gray-200';
      }
    };

    return (
      <div className="flex items-start space-x-4 p-4 bg-white rounded-xl hover:bg-gray-50 transition-all border border-gray-100">
        <div className={`p-2 rounded-lg ${getColor()} border`}>
          {getIcon()}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800">{activity.message}</p>
          <div className="flex items-center gap-2 mt-1">
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
          <span className={`text-xs px-2 py-1 rounded-full ${activity.resolved ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
            {activity.resolved ? 'Resolved' : 'Active'}
          </span>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center">
        <div className="text-center bg-white p-8 rounded-2xl shadow-lg">
          <AlertTriangle className="w-16 h-16 text-orange-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-800 mb-2">Error Loading Dashboard</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Retry
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
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-md">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-bold text-gray-800">Heimdall</h1>
              <p className="text-xs md:text-sm text-gray-500">User Dashboard</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center bg-white rounded-xl px-3 py-2 shadow">
              <Clock className="w-4 h-4 text-blue-500 mr-2" />
              <span className="text-xs md:text-sm font-medium text-gray-700">
                {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
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

        {/* Navigation Menu */}
        {menuOpen && (
          <div className="mb-6">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-3 sm:p-4">
              <nav className="flex flex-col sm:flex-row sm:flex-wrap gap-2 text-sm text-gray-700">
                <a href="/dashboard" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 bg-blue-50">
                  <Activity className="w-4 h-4 mr-2 text-blue-500" />Dashboard
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
                  <Bell className="w-4 h-4 mr-2 text-orange-500" />Alerts & Logs
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
        <div className="mb-8">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-800 mb-2">Welcome Back</h2>
          <p className="text-gray-600 flex items-center">
            <Activity className="w-4 h-4 mr-2" />
            {me?.username || me?.email || 'User'}
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            icon={Eye}
            title="Today's Matches"
            value={stats?.todayMatches || 0}
            subtitle={health ? `${health.matches24h} in 24h` : null}
            color="text-blue-600"
            bgColor="bg-blue-100"
          />
          <StatCard
            icon={Bell}
            title="Active Alerts"
            value={stats?.activeAlerts || 0}
            subtitle={health ? `${health.alerts24h} in 24h` : null}
            color="text-orange-600"
            bgColor="bg-orange-100"
          />
          <StatCard
            icon={Camera}
            title="Active Cameras"
            value={`${stats?.activeCameras || 0}/${stats?.totalCameras || 0}`}
            subtitle={stats?.cameraUptime ? `${stats.cameraUptime}% uptime` : null}
            color="text-purple-600"
            bgColor="bg-purple-100"
          />
          <StatCard
            icon={Shield}
            title="System Status"
            value={systemStatusInfo.text}
            subtitle={stats?.totalInmates ? `${stats.totalInmates} inmates` : null}
            color={systemStatusInfo.color}
            bgColor={systemStatusInfo.bgColor}
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Activity */}
          <div className="lg:col-span-2 bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-800">Recent Activity</h2>
              <button
                onClick={() => navigate('/admin/alerts')}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                View All
              </button>
            </div>
            <div className="space-y-3">
              {recentActivity.length > 0 ? (
                recentActivity.map(activity => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No recent activity</p>
                </div>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="space-y-6">
            {/* Quick Access */}
            <div className="bg-gradient-to-br from-blue-500 to-cyan-500 rounded-2xl shadow-lg p-6 text-white">
              <h3 className="text-lg font-bold mb-4">Quick Access</h3>
              <div className="space-y-3">
                <button
                  onClick={() => navigate('/admin/live')}
                  className="w-full bg-white/20 hover:bg-white/30 backdrop-blur-sm rounded-lg p-3 text-left transition-all border border-white/20"
                >
                  <div className="flex items-center">
                    <Camera className="w-5 h-5 mr-3" />
                    <span className="font-medium">View Live Cameras</span>
                  </div>
                </button>
                <button
                  onClick={() => navigate('/admin/alerts')}
                  className="w-full bg-white/20 hover:bg-white/30 backdrop-blur-sm rounded-lg p-3 text-left transition-all border border-white/20"
                >
                  <div className="flex items-center">
                    <Bell className="w-5 h-5 mr-3" />
                    <span className="font-medium">Check Alerts</span>
                  </div>
                </button>
                <button
                  onClick={() => navigate('/admin/upload')}
                  className="w-full bg-white/20 hover:bg-white/30 backdrop-blur-sm rounded-lg p-3 text-left transition-all border border-white/20"
                >
                  <div className="flex items-center">
                    <Eye className="w-5 h-5 mr-3" />
                    <span className="font-medium">Upload for Recognition</span>
                  </div>
                </button>
                <button
                  onClick={() => navigate('/admin/inmates')}
                  className="w-full bg-white/20 hover:bg-white/30 backdrop-blur-sm rounded-lg p-3 text-left transition-all border border-white/20"
                >
                  <div className="flex items-center">
                    <Users className="w-5 h-5 mr-3" />
                    <span className="font-medium">View Inmates</span>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
