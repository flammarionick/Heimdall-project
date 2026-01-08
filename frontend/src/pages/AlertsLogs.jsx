import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield,
  AlertTriangle,
  Clock,
  Menu,
  X,
  Monitor,
  Video,
  Camera,
  Users,
  BarChart3,
  LogOut,
  Search,
  Filter,
  Activity,
  CheckCircle,
  XCircle,
  Volume2,
  VolumeX
} from 'lucide-react';
import { useAlarm } from '../contexts/AlarmContext';

const BACKEND_BASE_URL = "";

export default function AlertsLogs() {
  const navigate = useNavigate();
  const { resolveAlarm, hasActiveAlarms, isAudioPlaying, stopAllAlarms } = useAlarm();
  const [me, setMe] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [filteredAlerts, setFilteredAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

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

  const fetchAlerts = async () => {
    try {
      const alertsRes = await fetch(`${BACKEND_BASE_URL}/api/alerts/`, {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (alertsRes.ok) {
        const alertsData = await alertsRes.json();
        const list = alertsData.alerts || alertsData || [];
        setAlerts(list);
        setFilteredAlerts(list);
      }
    } catch (err) {
      console.error('Failed to refresh alerts:', err);
    }
  };

  const handleResolveAlert = async (alertId) => {
    try {
      const res = await fetch(`${BACKEND_BASE_URL}/api/alerts/${alertId}/resolve`, {
        method: 'POST',
        credentials: 'include',
      });
      if (res.ok) {
        // Immediately stop alarm for this alert via AlarmContext
        resolveAlarm(alertId);
        // Refresh alerts list
        fetchAlerts();
      } else {
        console.error('Failed to resolve alert');
      }
    } catch (err) {
      console.error('Error resolving alert:', err);
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        const meRes = await fetch(`${BACKEND_BASE_URL}/auth/api/me`, {
          credentials: 'include',
          headers: { Accept: 'application/json' },
        });

        if (meRes.status === 401) {
          navigate('/login');
          return;
        }

        const meData = await meRes.json();
        setMe(meData);

        const alertsRes = await fetch(`${BACKEND_BASE_URL}/api/alerts/`, {
          credentials: 'include',
          headers: { Accept: 'application/json' },
        });

        if (!alertsRes.ok) {
          throw new Error('Failed to load alerts');
        }

        const alertsData = await alertsRes.json();
        const list = alertsData.alerts || alertsData || [];
        setAlerts(list);
        setFilteredAlerts(list);
      } catch (err) {
        console.error(err);
        setError('Unable to load alerts.');
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate]);

  useEffect(() => {
    let filtered = [...alerts];

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter((a) => {
        const title = (a.title || a.type || '').toLowerCase();
        const msg = (a.message || a.details || '').toLowerCase();
        const cam = (a.camera_name || a.camera || '').toLowerCase();
        return title.includes(q) || msg.includes(q) || cam.includes(q);
      });
    }

    if (statusFilter !== 'all') {
      // Backend returns 'resolved' as boolean, convert to status string for filtering
      filtered = filtered.filter((a) => {
        const status = a.resolved ? 'resolved' : 'open';
        return status === statusFilter;
      });
    }

    setFilteredAlerts(filtered);
  }, [alerts, searchQuery, statusFilter]);

  const formatTime = (ts) => {
    if (!ts) return '—';
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return ts;
    return d.toLocaleString();
  };

  const stats = {
    total: alerts.length,
    open: alerts.filter((a) => !a.resolved).length,
    resolved: alerts.filter((a) => a.resolved === true).length,
    critical: alerts.filter((a) => (a.level || '').toLowerCase() === 'danger').length,
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading alerts…</p>
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

  const StatCard = ({ icon: Icon, title, value, color, bgColor }) => (
    <div className="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all transform hover:scale-[1.02] border border-gray-100">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-xl ${bgColor}`}>
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
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
              <p className="text-xs md:text-sm text-gray-500">{me?.email || 'Alerts & Logs'}</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center bg-white rounded-xl px-3 py-2 shadow">
              <Clock className="w-4 h-4 text-blue-500 mr-2" />
              <span className="text-xs md:text-sm font-medium text-gray-700">
                {new Date().toLocaleDateString('en-US', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
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
                <a href="/admin/alerts" className="flex items-center px-3 py-2 rounded-xl bg-blue-50">
                  <AlertTriangle className="w-4 h-4 mr-2 text-orange-500" />
                  Alerts & Logs
                </a>
                <a href="/admin/analytics" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
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

        {/* Active Alarm Banner */}
        {hasActiveAlarms && (
          <div className="mb-6 bg-red-600 rounded-2xl p-4 shadow-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 text-white">
                {isAudioPlaying ? (
                  <Volume2 className="w-6 h-6 animate-pulse" />
                ) : (
                  <VolumeX className="w-6 h-6" />
                )}
                <div>
                  <h3 className="font-bold text-lg">Active Alarm</h3>
                  <p className="text-red-100 text-sm">
                    {isAudioPlaying ? 'Alarm sounding - resolve alerts below to stop' : 'Silent period - alarm will resume shortly'}
                  </p>
                </div>
              </div>
              <button
                onClick={stopAllAlarms}
                className="bg-white text-red-600 px-4 py-2 rounded-xl font-semibold hover:bg-red-50 transition-colors flex items-center gap-2"
              >
                <VolumeX className="w-4 h-4" />
                Emergency Stop
              </button>
            </div>
          </div>
        )}

        {/* Title */}
        <div className="mb-6">
          <h2 className="text-2xl md:text-3xl font-bold text-gray-800 mb-2">Alerts & Logs</h2>
          <p className="text-gray-600 flex items-center">
            <Activity className="w-4 h-4 mr-2 text-blue-500" />
            Review system alerts and activity logs
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard icon={AlertTriangle} title="Total Alerts" value={stats.total} color="text-blue-600" bgColor="bg-blue-100" />
          <StatCard icon={Activity} title="Open" value={stats.open} color="text-orange-600" bgColor="bg-orange-100" />
          <StatCard icon={CheckCircle} title="Resolved" value={stats.resolved} color="text-green-600" bgColor="bg-green-100" />
          <StatCard icon={XCircle} title="Critical" value={stats.critical} color="text-red-600" bgColor="bg-red-100" />
        </div>

        {/* Filters */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search alerts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>

            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                <option value="all">All statuses</option>
                <option value="open">Open</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>

            <div className="flex items-center justify-end text-sm text-gray-500">
              Showing <span className="font-semibold text-gray-700 mx-1">{filteredAlerts.length}</span> of{' '}
              <span className="font-semibold text-gray-700 mx-1">{alerts.length}</span> alerts
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Type', 'Message', 'Camera', 'Status', 'Time', 'Actions'].map((h) => (
                    <th key={h} className="px-6 py-4 text-left text-sm font-semibold text-gray-700">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredAlerts.map((a, idx) => (
                  <tr key={a.id || idx} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <AlertTriangle className="w-4 h-4 text-orange-500 mr-2" />
                        <span className="font-medium text-gray-800">{a.title || a.type || 'Alert'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-gray-700">{a.message || a.details || '—'}</p>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-600">{a.camera_name || a.camera || '—'}</span>
                    </td>
                    <td className="px-6 py-4">
                      {a.resolved ? (
                        <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">
                          Resolved
                        </span>
                      ) : (
                        <span className="px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-semibold">
                          Open
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center text-gray-600">
                        <Clock className="w-4 h-4 mr-2 text-gray-400" />
                        <span className="text-sm">{formatTime(a.timestamp || a.created_at)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {!a.resolved && (
                        <button
                          onClick={() => handleResolveAlert(a.id)}
                          className="px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 transition-colors flex items-center"
                        >
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Resolve
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredAlerts.length === 0 && (
            <div className="text-center py-12">
              <AlertTriangle className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No alerts found</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}