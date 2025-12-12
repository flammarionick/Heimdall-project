// src/pages/LiveMonitoring.jsx
import { useState } from 'react';
import { Camera, MapPin, Plus, Edit, Trash2, Power, Video, AlertCircle, CheckCircle2, XCircle, Shield, Menu, X, Monitor, Users, AlertTriangle, BarChart3, Upload, LogOut, Clock } from 'lucide-react';

const BACKEND_BASE_URL = "http://127.0.0.1:5000";

export default function LiveMonitoring() {
  const [cameras, setCameras] = useState([
    { id: 1, name: 'Main Entrance', location: 'Building A - Floor 1', status: true, lastSeen: '2 mins ago', alerts: 0 },
    { id: 2, name: 'Checkpoint Alpha', location: 'Building A - Floor 2', status: true, lastSeen: '5 mins ago', alerts: 2 },
    { id: 3, name: 'Corridor B', location: 'Building B - Floor 1', status: false, lastSeen: '15 mins ago', alerts: 0 },
    { id: 4, name: 'East Wing Exit', location: 'Building C - Floor 1', status: true, lastSeen: '1 min ago', alerts: 1 },
    { id: 5, name: 'Cafeteria Monitor', location: 'Building A - Ground', status: true, lastSeen: '3 mins ago', alerts: 0 },
    { id: 6, name: 'Recreation Area', location: 'Building D - Outdoor', status: true, lastSeen: '4 mins ago', alerts: 0 }
  ]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData] = useState({ name: '', location: '' });
  const [filter, setFilter] = useState('all');
  const [menuOpen, setMenuOpen] = useState(false);

  const toggleStatus = (id) => {
    setCameras(prev =>
      prev.map(cam => cam.id === id ? { ...cam, status: !cam.status } : cam)
    );
  };

  const deleteCamera = (id) => {
    if (window.confirm('Are you sure you want to delete this camera?')) {
      setCameras(prev => prev.filter(cam => cam.id !== id));
    }
  };

  const addCamera = () => {
    if (!formData.name || !formData.location) {
      alert('Please fill in all fields');
      return;
    }
    const newCamera = {
      id: cameras.length + 1,
      name: formData.name,
      location: formData.location,
      status: true,
      lastSeen: 'Just now',
      alerts: 0
    };
    setCameras(prev => [...prev, newCamera]);
    setFormData({ name: '', location: '' });
    setShowAddModal(false);
  };

  const filteredCameras = filter === 'all' 
    ? cameras 
    : cameras.filter(cam => filter === 'active' ? cam.status : !cam.status);

  const stats = {
    total: cameras.length,
    active: cameras.filter(c => c.status).length,
    offline: cameras.filter(c => !c.status).length,
    alerts: cameras.reduce((sum, c) => sum + c.alerts, 0)
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
              <h1 className="text-xl md:text-2xl font-bold text-gray-800">Heimdall Admin</h1>
              <p className="text-xs md:text-sm text-gray-500">Live Monitoring</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center bg-white rounded-xl px-3 py-2 shadow">
              <Clock className="w-4 h-4 text-blue-500 mr-2" />
              <span className="text-xs md:text-sm font-medium text-gray-700">
                {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
              </span>
            </div>
            <button onClick={() => setMenuOpen((v) => !v)} className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white shadow-md border border-gray-100 hover:bg-gray-50 transition">
              {menuOpen ? <X className="w-5 h-5 text-gray-700" /> : <Menu className="w-5 h-5 text-gray-700" />}
            </button>
          </div>
        </header>

        {/* Hamburger dropdown menu */}
        {menuOpen && (
          <div className="mb-6">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-3 sm:p-4">
              <nav className="flex flex-col sm:flex-row sm:flex-wrap gap-2 text-sm text-gray-700">
                <a href="/admin/dashboard" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Monitor className="w-4 h-4 mr-2 text-blue-500" />Dashboard
                </a>
                <a href="/admin/live" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 bg-blue-50">
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
                <a href="/admin/users" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Shield className="w-4 h-4 mr-2 text-gray-700" />Manage Users
                </a>
                <a href={`${BACKEND_BASE_URL}/auth/logout`} className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 sm:ml-auto">
                  <LogOut className="w-4 h-4 mr-2 text-red-500" />Logout
                </a>
              </nav>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-3xl font-bold text-gray-800 mb-2">Live Monitoring</h2>
              <p className="text-gray-600 flex items-center">
                <Video className="w-4 h-4 mr-2" />
                Real-time camera feed monitoring
              </p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:scale-105 transition-all"
            >
              <Plus className="w-5 h-5 mr-2" />
              Add Camera
            </button>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl p-4 shadow-md border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm font-medium">Total Cameras</p>
                  <p className="text-2xl font-bold text-gray-800">{stats.total}</p>
                </div>
                <div className="p-3 bg-blue-100 rounded-lg">
                  <Camera className="w-6 h-6 text-blue-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-md border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm font-medium">Active</p>
                  <p className="text-2xl font-bold text-green-600">{stats.active}</p>
                </div>
                <div className="p-3 bg-green-100 rounded-lg">
                  <CheckCircle2 className="w-6 h-6 text-green-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-md border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm font-medium">Offline</p>
                  <p className="text-2xl font-bold text-red-600">{stats.offline}</p>
                </div>
                <div className="p-3 bg-red-100 rounded-lg">
                  <XCircle className="w-6 h-6 text-red-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-md border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm font-medium">Active Alerts</p>
                  <p className="text-2xl font-bold text-orange-600">{stats.alerts}</p>
                </div>
                <div className="p-3 bg-orange-100 rounded-lg">
                  <AlertCircle className="w-6 h-6 text-orange-600" />
                </div>
              </div>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex gap-2 bg-white p-2 rounded-xl shadow-md border border-gray-100 w-fit">
            {['all', 'active', 'offline'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                  filter === f
                    ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Camera Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCameras.map((camera) => (
            <div
              key={camera.id}
              className="bg-white rounded-2xl shadow-lg hover:shadow-xl transition-all border border-gray-100 overflow-hidden group"
            >
              {/* Camera Feed Preview */}
              <div className="relative bg-gradient-to-br from-gray-800 to-gray-900 h-48 flex items-center justify-center">
                <div className="absolute inset-0 bg-black/20"></div>
                <Video className="w-16 h-16 text-gray-600" />
                <div className="absolute top-3 left-3 flex items-center gap-2">
                  <div className={`flex items-center px-3 py-1.5 rounded-full ${
                    camera.status 
                      ? 'bg-green-500/90' 
                      : 'bg-red-500/90'
                  } backdrop-blur-sm`}>
                    <div className={`w-2 h-2 rounded-full mr-2 ${
                      camera.status ? 'bg-white animate-pulse' : 'bg-white/50'
                    }`}></div>
                    <span className="text-white text-xs font-semibold">
                      {camera.status ? 'LIVE' : 'OFFLINE'}
                    </span>
                  </div>
                </div>
                {camera.alerts > 0 && (
                  <div className="absolute top-3 right-3 bg-red-500 text-white px-2 py-1 rounded-full text-xs font-bold flex items-center">
                    <AlertCircle className="w-3 h-3 mr-1" />
                    {camera.alerts}
                  </div>
                )}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-4">
                  <p className="text-white text-xs">Last activity: {camera.lastSeen}</p>
                </div>
              </div>

              {/* Camera Info */}
              <div className="p-5">
                <div className="mb-4">
                  <h3 className="text-lg font-bold text-gray-800 mb-1">{camera.name}</h3>
                  <div className="flex items-center text-gray-500 text-sm">
                    <MapPin className="w-4 h-4 mr-1" />
                    {camera.location}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <button
                    onClick={() => toggleStatus(camera.id)}
                    className={`flex-1 flex items-center justify-center px-3 py-2 rounded-lg font-medium text-sm transition-all ${
                      camera.status
                        ? 'bg-orange-100 text-orange-600 hover:bg-orange-200'
                        : 'bg-green-100 text-green-600 hover:bg-green-200'
                    }`}
                  >
                    <Power className="w-4 h-4 mr-1" />
                    {camera.status ? 'Disable' : 'Enable'}
                  </button>
                  <button className="p-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition-all">
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteCamera(camera.id)}
                    className="p-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Add Camera Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Add New Camera</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Camera Name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., Main Entrance"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Location
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., Building A - Floor 1"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-xl font-semibold hover:bg-gray-200 transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={addCamera}
                  className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-semibold hover:from-blue-600 hover:to-cyan-600 transition-all shadow-lg"
                >
                  Add Camera
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}