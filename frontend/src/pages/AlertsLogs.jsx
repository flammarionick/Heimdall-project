// src/pages/AlertsLogs.jsx
import { useState } from 'react';
import { AlertTriangle, CheckCircle, Clock, User, Camera, Search, Download, Eye, Shield, Menu, X, Monitor, Video, Users, Bell, BarChart3, Upload, Settings, LogOut } from 'lucide-react';

const BACKEND_BASE_URL = "http://127.0.0.1:5000";

export default function AlertsLogs() {
  const [alerts, setAlerts] = useState([
    {
      id: 1,
      timestamp: new Date('2024-12-02T10:30:00'),
      message: 'High-risk inmate detected at Main Entrance',
      level: 'critical',
      inmate_id: 'INM-2341',
      inmate_name: 'John Doe',
      camera: 'Main Entrance',
      resolved: false
    },
    {
      id: 2,
      timestamp: new Date('2024-12-02T09:15:00'),
      message: 'Facial recognition match at Checkpoint Alpha',
      level: 'warning',
      inmate_id: 'INM-1892',
      inmate_name: 'Jane Smith',
      camera: 'Checkpoint Alpha',
      resolved: true
    },
    {
      id: 3,
      timestamp: new Date('2024-12-02T08:45:00'),
      message: 'Multiple detection attempts at East Wing',
      level: 'info',
      inmate_id: 'INM-3421',
      inmate_name: 'Michael Johnson',
      camera: 'East Wing Exit',
      resolved: false
    }
  ]);

  const [filter, setFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);

  const handleResolve = (alertId) => {
    setAlerts(prev =>
      prev.map(a => (a.id === alertId ? { ...a, resolved: true } : a))
    );
  };

  const getLevelColor = (level) => {
    switch (level) {
      case 'critical': return 'bg-red-100 text-red-700 border-red-200';
      case 'warning': return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'info': return 'bg-blue-100 text-blue-700 border-blue-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const getLevelIcon = (level) => {
    return <AlertTriangle className="w-5 h-5" />;
  };

  const filteredAlerts = alerts.filter(alert => {
    const matchesFilter =
      filter === 'all' ||
      (filter === 'resolved' && alert.resolved) ||
      (filter === 'unresolved' && !alert.resolved) ||
      (filter === alert.level);
    
    const matchesSearch =
      searchQuery === '' ||
      alert.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (alert.inmate_name && alert.inmate_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      alert.camera.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesFilter && matchesSearch;
  });

  const stats = {
    total: alerts.length,
    resolved: alerts.filter(a => a.resolved).length,
    unresolved: alerts.filter(a => !a.resolved).length,
    critical: alerts.filter(a => a.level === 'critical').length
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Top bar with logo + hamburger */}
        <header className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-md">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-bold text-gray-800">Heimdall</h1>
              <p className="text-xs md:text-sm text-gray-500">Alerts & Logs</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center bg-white rounded-xl px-3 py-2 shadow">
              <Clock className="w-4 h-4 text-blue-500 mr-2" />
              <span className="text-xs md:text-sm font-medium text-gray-700">
                {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
              </span>
            </div>
            <button onClick={() => setMenuOpen((v) => !v)} className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white shadow-md border border-gray-100 hover:bg-gray-50 transition">
              {menuOpen ? <X className="w-5 h-5 text-gray-700" /> : <Menu className="w-5 h-5 text-gray-700" />}
            </button>
          </div>
        </header>

        {/* Hamburger Menu */}
        {menuOpen && (
          <div className="mb-6">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-3 sm:p-4">
              <nav className="flex flex-col sm:flex-row sm:flex-wrap gap-2 text-sm text-gray-700">
                <a href="/admin" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Monitor className="w-4 h-4 mr-2 text-blue-500" />Dashboard
                </a>
                <a href="/monitoring" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Video className="w-4 h-4 mr-2 text-purple-500" />Live Monitoring
                </a>
                <a href="/inmates" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Users className="w-4 h-4 mr-2 text-emerald-500" />Inmates
                </a>
                <a href="/cameras" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Camera className="w-4 h-4 mr-2 text-indigo-500" />Cameras
                </a>
                <a
  href="/admin/alerts"
  className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 bg-blue-50"
>
  <Bell className="w-4 h-4 mr-2 text-orange-500" />
  Alerts & Logs
</a>

                <a href="/analytics" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <BarChart3 className="w-4 h-4 mr-2 text-cyan-500" />Analytics
                </a>
                <a href="/upload" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Upload className="w-4 h-4 mr-2 text-pink-500" />Upload
                </a>
                <a href="/users" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Settings className="w-4 h-4 mr-2 text-gray-500" />Manage Users
                </a>
                <a href={`${BACKEND_BASE_URL}/auth/logout`} className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 sm:ml-auto">
                  <LogOut className="w-4 h-4 mr-2 text-red-500" />Logout
                </a>
              </nav>
            </div>
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 shadow-md border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">Total Alerts</p>
                <p className="text-2xl font-bold text-gray-800">{stats.total}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-md border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">Resolved</p>
                <p className="text-2xl font-bold text-green-600">{stats.resolved}</p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-md border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">Unresolved</p>
                <p className="text-2xl font-bold text-orange-600">{stats.unresolved}</p>
              </div>
              <div className="p-3 bg-orange-100 rounded-lg">
                <Clock className="w-6 h-6 text-orange-600" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-md border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">Critical</p>
                <p className="text-2xl font-bold text-red-600">{stats.critical}</p>
              </div>
              <div className="p-3 bg-red-100 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Filters and Search */}
        <div className="bg-white rounded-xl shadow-md border border-gray-100 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search alerts, inmates, or cameras..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
            <div className="flex gap-2 flex-wrap">
              {['all', 'critical', 'warning', 'info', 'resolved', 'unresolved'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-4 py-2.5 rounded-lg font-medium text-sm transition-all ${
                    filter === f
                      ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-md'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Alerts List */}
        <div className="space-y-4">
          {filteredAlerts.length === 0 ? (
            <div className="bg-white rounded-xl p-12 text-center shadow-md border border-gray-100">
              <AlertTriangle className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 text-lg">No alerts found matching your criteria</p>
            </div>
          ) : (
            filteredAlerts.map((alert) => (
              <div key={alert.id} className="bg-white rounded-xl shadow-md hover:shadow-lg transition-all border border-gray-100 p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    <div className={`p-3 rounded-lg ${getLevelColor(alert.level)} border`}>
                      {getLevelIcon(alert.level)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-bold text-gray-800">{alert.message}</h3>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${alert.resolved ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                          {alert.resolved ? 'Resolved' : 'Active'}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div className="flex items-center text-gray-600">
                          <Clock className="w-4 h-4 mr-2 text-gray-400" />
                          {alert.timestamp.toLocaleString()}
                        </div>
                        <div className="flex items-center text-gray-600">
                          <User className="w-4 h-4 mr-2 text-gray-400" />
                          {alert.inmate_name}
                        </div>
                        <div className="flex items-center text-gray-600">
                          <Camera className="w-4 h-4 mr-2 text-gray-400" />
                          {alert.camera}
                        </div>
                        {alert.inmate_id && (
                          <div className="flex items-center text-gray-600">
                            <span className="font-mono text-sm">{alert.inmate_id}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 ml-4">
                    {alert.inmate_id && (
                      <button className="p-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition-all">
                        <Eye className="w-5 h-5" />
                      </button>
                    )}
                    {!alert.resolved && (
                      <button onClick={() => handleResolve(alert.id)} className="px-4 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-all font-medium text-sm">
                        Resolve
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}