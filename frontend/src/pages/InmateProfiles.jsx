import { useState } from 'react';
import { Search, Filter, User, MapPin, Calendar, AlertTriangle, Plus, Eye, Edit, Trash2, Shield, Menu, X, Monitor, Video, Camera, BarChart3, Upload, LogOut, Clock } from 'lucide-react';

const BACKEND_BASE_URL = "http://127.0.0.1:5000";

export default function InmateProfiles() {
  const [inmates, setInmates] = useState([
    {
      id: 'INM-2341',
      name: 'John Doe',
      age: 34,
      status: 'Escaped',
      location: 'Kuje Correctional Facility',
      crime: 'Armed Robbery',
      riskLevel: 'High',
      lastSeen: 'July 5, 2022',
      image: 'https://via.placeholder.com/150'
    },
    {
      id: 'INM-1892',
      name: 'Jane Smith',
      age: 28,
      status: 'Incarcerated',
      location: 'Abuja Maximum Security',
      crime: 'Fraud',
      riskLevel: 'Medium',
      lastSeen: 'Active',
      image: 'https://via.placeholder.com/150'
    },
    {
      id: 'INM-3421',
      name: 'Michael Johnson',
      age: 42,
      status: 'Released',
      location: 'Lagos Central Prison',
      crime: 'Theft',
      riskLevel: 'Low',
      lastSeen: 'March 15, 2024',
      image: 'https://via.placeholder.com/150'
    },
    {
      id: 'INM-8765',
      name: 'Robert Brown',
      age: 38,
      status: 'Escaped',
      location: 'Kuje Correctional Facility',
      crime: 'Assault',
      riskLevel: 'High',
      lastSeen: 'July 5, 2022',
      image: 'https://via.placeholder.com/150'
    }
  ]);

  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const getRiskColor = (level) => {
    switch (level) {
      case 'High': return 'bg-red-100 text-red-700 border-red-200';
      case 'Medium': return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'Low': return 'bg-green-100 text-green-700 border-green-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'Escaped': return 'bg-red-500';
      case 'Incarcerated': return 'bg-blue-500';
      case 'Released': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const filteredInmates = inmates.filter(inmate => {
    const matchesSearch = inmate.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         inmate.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterStatus === 'all' || inmate.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  const stats = {
    total: inmates.length,
    escaped: inmates.filter(i => i.status === 'Escaped').length,
    incarcerated: inmates.filter(i => i.status === 'Incarcerated').length,
    released: inmates.filter(i => i.status === 'Released').length
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
              <p className="text-xs md:text-sm text-gray-500">Inmate Profiles</p>
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
                <a href="/admin/inmates" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 bg-blue-50">
                  <User className="w-4 h-4 mr-2 text-emerald-500" />Inmate Profiles
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
              <h2 className="text-3xl font-bold text-gray-800 mb-2">Inmate Profiles</h2>
              <p className="text-gray-600 flex items-center">
                <User className="w-4 h-4 mr-2" />
                Manage and view all registered inmates
              </p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:scale-105 transition-all"
            >
              <Plus className="w-5 h-5 mr-2" />
              Add Inmate
            </button>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl p-4 shadow-md border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm font-medium">Total Inmates</p>
                  <p className="text-2xl font-bold text-gray-800">{stats.total}</p>
                </div>
                <div className="p-3 bg-blue-100 rounded-lg">
                  <User className="w-6 h-6 text-blue-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-md border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm font-medium">Escaped</p>
                  <p className="text-2xl font-bold text-red-600">{stats.escaped}</p>
                </div>
                <div className="p-3 bg-red-100 rounded-lg">
                  <AlertTriangle className="w-6 h-6 text-red-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-md border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm font-medium">Incarcerated</p>
                  <p className="text-2xl font-bold text-blue-600">{stats.incarcerated}</p>
                </div>
                <div className="p-3 bg-blue-100 rounded-lg">
                  <User className="w-6 h-6 text-blue-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-md border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm font-medium">Released</p>
                  <p className="text-2xl font-bold text-green-600">{stats.released}</p>
                </div>
                <div className="p-3 bg-green-100 rounded-lg">
                  <User className="w-6 h-6 text-green-600" />
                </div>
              </div>
            </div>
          </div>

          {/* Search and Filters */}
          <div className="bg-white rounded-xl shadow-md border border-gray-100 p-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by name or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>

              <div className="flex gap-2">
                {['all', 'Escaped', 'Incarcerated', 'Released'].map(filter => (
                  <button
                    key={filter}
                    onClick={() => setFilterStatus(filter)}
                    className={`px-4 py-2.5 rounded-lg font-medium text-sm transition-all ${
                      filterStatus === filter
                        ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-md'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {filter === 'all' ? 'All' : filter}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Inmates Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredInmates.map(inmate => (
            <div key={inmate.id} className="bg-white rounded-2xl shadow-lg hover:shadow-xl transition-all border border-gray-100 overflow-hidden">
              {/* Header with status */}
              <div className="relative h-32 bg-gradient-to-br from-blue-500 to-cyan-500 p-4">
                <div className={`absolute top-3 right-3 px-3 py-1 ${getStatusColor(inmate.status)} text-white text-xs font-bold rounded-full`}>
                  {inmate.status}
                </div>
              </div>

              {/* Profile Image */}
              <div className="relative px-6 -mt-16">
                <div className="w-32 h-32 mx-auto rounded-full border-4 border-white shadow-lg overflow-hidden bg-gray-200">
                  <User className="w-full h-full text-gray-400 p-6" />
                </div>
              </div>

              {/* Inmate Details */}
              <div className="p-6 pt-4">
                <div className="text-center mb-4">
                  <h3 className="text-xl font-bold text-gray-800 mb-1">{inmate.name}</h3>
                  <p className="text-sm text-gray-500">{inmate.id}</p>
                </div>

                <div className="space-y-3 mb-4">
                  <div className="flex items-center text-sm text-gray-600">
                    <User className="w-4 h-4 mr-2 text-gray-400" />
                    <span>{inmate.age} years old</span>
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <MapPin className="w-4 h-4 mr-2 text-gray-400" />
                    <span className="truncate">{inmate.location}</span>
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <Calendar className="w-4 h-4 mr-2 text-gray-400" />
                    <span>Last seen: {inmate.lastSeen}</span>
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <AlertTriangle className="w-4 h-4 mr-2 text-gray-400" />
                    <span>{inmate.crime}</span>
                  </div>
                </div>

                {/* Risk Level Badge */}
                <div className="mb-4">
                  <span className={`inline-block px-3 py-1 text-xs font-bold rounded-full border ${getRiskColor(inmate.riskLevel)}`}>
                    Risk Level: {inmate.riskLevel}
                  </span>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button className="flex-1 px-3 py-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition-all font-medium text-sm flex items-center justify-center">
                    <Eye className="w-4 h-4 mr-1" />
                    View
                  </button>
                  <button className="px-3 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-all">
                    <Edit className="w-4 h-4" />
                  </button>
                  <button className="px-3 py-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-all">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredInmates.length === 0 && (
          <div className="bg-white rounded-xl p-12 text-center shadow-md border border-gray-100">
            <User className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 text-lg">No inmates found matching your criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}