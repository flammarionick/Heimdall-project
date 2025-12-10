import { useState } from 'react';
import { Camera, MapPin, Plus, Edit, Trash2, Power, Video, Settings, CheckCircle2, XCircle } from 'lucide-react';

export default function ManageCameras() {
  const [cameras, setCamera] = useState([
    { id: 1, name: 'Main Entrance', location: 'Building A - Floor 1', status: true, fps: 30, resolution: '1080p' },
    { id: 2, name: 'Checkpoint Alpha', location: 'Building A - Floor 2', status: true, fps: 30, resolution: '1080p' },
    { id: 3, name: 'Corridor B', location: 'Building B - Floor 1', status: false, fps: 0, resolution: '1080p' },
    { id: 4, name: 'East Wing Exit', location: 'Building C - Floor 1', status: true, fps: 25, resolution: '720p' },
    { id: 5, name: 'Cafeteria Monitor', location: 'Building A - Ground', status: true, fps: 30, resolution: '1080p' },
    { id: 6, name: 'Recreation Area', location: 'Building D - Outdoor', status: true, fps: 30, resolution: '4K' }
  ]);

  const [showAddModal, setShowAddModal] = useState(false);

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
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-4xl font-bold text-gray-800 mb-2">Camera Management</h1>
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