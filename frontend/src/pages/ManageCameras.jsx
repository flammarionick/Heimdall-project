import { useState } from 'react';
import { Camera, MapPin, Plus, Edit, Trash2, Power, Video, Settings, CheckCircle2, XCircle, Shield, Menu, X, Monitor, Users, AlertTriangle, BarChart3, Upload, LogOut, Clock } from 'lucide-react';

const BACKEND_BASE_URL = "http://127.0.0.1:5000";

export default function ManageCameras() {
  const [cameras, setCameras] = useState([
    { id: 1, name: 'Main Entrance', location: 'Building A - Floor 1', status: true, fps: 30, resolution: '1080p' },
    { id: 2, name: 'Checkpoint Alpha', location: 'Building A - Floor 2', status: true, fps: 30, resolution: '1080p' },
    { id: 3, name: 'Corridor B', location: 'Building B - Floor 1', status: false, fps: 0, resolution: '1080p' },
    { id: 4, name: 'East Wing Exit', location: 'Building C - Floor 1', status: true, fps: 25, resolution: '720p' },
    { id: 5, name: 'Cafeteria Monitor', location: 'Building A - Ground', status: true, fps: 30, resolution: '1080p' },
    { id: 6, name: 'Recreation Area', location: 'Building D - Outdoor', status: true, fps: 30, resolution: '4K' }
  ]);

  const [showAddModal, setShowAddModal] = useState(false);
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

  const stats = {
    total: cameras.length,
    online: cameras.filter(c => c.status).length,
    offline: cameras.filter(c => c.status === false).length,
    avgFps: Math.round(cameras.filter(c => c.status).reduce((acc, c) => acc + c.fps, 0) / cameras.filter(c => c.status).length)
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
              <p className="text-xs md:text-sm text-gray-500">Camera Management</p>
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
                <a href="/admin/cameras" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 bg-blue-50">
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
              <h2 className="text-3xl font-bold text-gray-800 mb-2">Camera Management</h2>
              <p className="text-gray-600 flex items-center">
                <Video className="w-4 h-4 mr-2" />
                Configure and monitor all camera streams
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

          {/* Stats Grid */}
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
                  <p className="text-gray-500 text-sm font-medium">Online</p>
                  <p className="text-2xl font-bold text-green-600">{stats.online}</p>
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
                  <p className="text-gray-500 text-sm font-medium">Avg FPS</p>
                  <p className="text-2xl font-bold text-purple-600">{stats.avgFps}</p>
                </div>
                <div className="p-3 bg-purple-100 rounded-lg">
                  <Video className="w-6 h-6 text-purple-600" />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Cameras List */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Status</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Camera Name</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Location</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Resolution</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">FPS</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {cameras.map((camera) => (
                  <tr key={camera.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        {camera.status ? (
                          <>
                            <div className="w-3 h-3 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                            <span className="text-sm font-medium text-green-600">Online</span>
                          </>
                        ) : (
                          <>
                            <div className="w-3 h-3 bg-red-500 rounded-full mr-2"></div>
                            <span className="text-sm font-medium text-red-600">Offline</span>
                          </>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="p-2 bg-blue-100 rounded-lg mr-3">
                          <Camera className="w-5 h-5 text-blue-600" />
                        </div>
                        <span className="font-medium text-gray-800">{camera.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center text-gray-600">
                        <MapPin className="w-4 h-4 mr-2 text-gray-400" />
                        <span className="text-sm">{camera.location}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
                        {camera.resolution}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm font-medium text-gray-700">
                        {camera.status ? `${camera.fps} FPS` : '—'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => toggleStatus(camera.id)}
                          className={`p-2 rounded-lg transition-all ${
                            camera.status
                              ? 'bg-orange-100 text-orange-600 hover:bg-orange-200'
                              : 'bg-green-100 text-green-600 hover:bg-green-200'
                          }`}
                          title={camera.status ? 'Turn Off' : 'Turn On'}
                        >
                          <Power className="w-4 h-4" />
                        </button>
                        <button className="p-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition-all" title="Settings">
                          <Settings className="w-4 h-4" />
                        </button>
                        <button className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-all" title="Edit">
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => deleteCamera(camera.id)}
                          className="p-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-all"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}