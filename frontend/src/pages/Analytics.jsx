import { useState } from 'react';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { BarChart3, TrendingUp, Users, Camera, Clock, Download, Shield, Menu, X, Monitor, Video, AlertTriangle, Upload, LogOut } from 'lucide-react';

const BACKEND_BASE_URL = "http://127.0.0.1:5000";

export default function Analytics() {
  const [timeRange, setTimeRange] = useState('month');
  const [menuOpen, setMenuOpen] = useState(false);

  const matchesData = [
    { month: 'Jan', matches: 65, alerts: 12 },
    { month: 'Feb', matches: 89, alerts: 18 },
    { month: 'Mar', matches: 123, alerts: 25 },
    { month: 'Apr', matches: 95, alerts: 15 },
    { month: 'May', matches: 142, alerts: 28 },
    { month: 'Jun', matches: 178, alerts: 32 }
  ];

  const locationData = [
    { location: 'Main Entrance', count: 523 },
    { location: 'Checkpoint Alpha', count: 412 },
    { location: 'East Wing', count: 301 },
    { location: 'Cafeteria', count: 198 },
    { location: 'Recreation Area', count: 156 }
  ];

  const hourlyData = [
    { hour: '00:00', count: 12 },
    { hour: '04:00', count: 8 },
    { hour: '08:00', count: 45 },
    { hour: '12:00', count: 89 },
    { hour: '16:00', count: 67 },
    { hour: '20:00', count: 34 }
  ];

  const riskDistribution = [
    { name: 'High Risk', value: 234, color: '#ef4444' },
    { name: 'Medium Risk', value: 456, color: '#f59e0b' },
    { name: 'Low Risk', value: 312, color: '#10b981' }
  ];

  const StatCard = ({ icon: Icon, title, value, change, color }) => (
    <div className="bg-white rounded-xl p-6 shadow-md border border-gray-100">
      <div className="flex items-center justify-between mb-2">
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6" />
        </div>
        {change && (
          <span className={`text-sm font-semibold ${change > 0 ? 'text-green-600' : 'text-red-600'}`}>
            {change > 0 ? '+' : ''}{change}%
          </span>
        )}
      </div>
      <h3 className="text-sm font-medium text-gray-600">{title}</h3>
      <p className="text-2xl font-bold text-gray-800 mt-1">{value}</p>
    </div>
  );

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
              <p className="text-xs md:text-sm text-gray-500">Analytics Dashboard</p>
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
                <a href="/admin/analytics" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 bg-blue-50">
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
              <h2 className="text-3xl font-bold text-gray-800 mb-2">Analytics Dashboard</h2>
              <p className="text-gray-600 flex items-center">
                <BarChart3 className="w-4 h-4 mr-2" />
                Comprehensive system insights and trends
              </p>
            </div>
            <div className="flex items-center gap-3">
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="px-4 py-2 bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 font-medium text-gray-700"
              >
                <option value="week">Last Week</option>
                <option value="month">Last Month</option>
                <option value="quarter">Last Quarter</option>
                <option value="year">Last Year</option>
              </select>
              <button className="flex items-center px-4 py-2 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg font-medium text-gray-700 transition-all">
                <Download className="w-4 h-4 mr-2" />
                Export
              </button>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <StatCard
              icon={TrendingUp}
              title="Total Matches"
              value="2,341"
              change={12.5}
              color="bg-blue-100 text-blue-600"
            />
            <StatCard
              icon={Users}
              title="Unique Individuals"
              value="847"
              change={8.3}
              color="bg-purple-100 text-purple-600"
            />
            <StatCard
              icon={Camera}
              title="Active Cameras"
              value="42"
              change={5.2}
              color="bg-green-100 text-green-600"
            />
            <StatCard
              icon={Clock}
              title="Avg Response Time"
              value="0.3s"
              change={-15.4}
              color="bg-orange-100 text-orange-600"
            />
          </div>
        </div>

        {/* Charts Grid */}
        <div className="space-y-6">
          {/* Matches Over Time */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-800">Recognition Trends</h2>
              <div className="flex items-center gap-2 text-sm">
                <div className="flex items-center">
                  <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
                  <span className="text-gray-600">Matches</span>
                </div>
                <div className="flex items-center ml-4">
                  <div className="w-3 h-3 bg-orange-500 rounded-full mr-2"></div>
                  <span className="text-gray-600">Alerts</span>
                </div>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={matchesData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '12px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                  }}
                />
                <Line type="monotone" dataKey="matches" stroke="#3b82f6" strokeWidth={3} dot={{ fill: '#3b82f6', r: 5 }} />
                <Line type="monotone" dataKey="alerts" stroke="#f59e0b" strokeWidth={3} dot={{ fill: '#f59e0b', r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Locations Bar Chart */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
              <h2 className="text-xl font-bold text-gray-800 mb-6">Top Locations</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={locationData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" stroke="#9ca3af" />
                  <YAxis dataKey="location" type="category" stroke="#9ca3af" width={120} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e5e7eb',
                      borderRadius: '12px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                    }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" radius={[0, 8, 8, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Risk Distribution Pie Chart */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
              <h2 className="text-xl font-bold text-gray-800 mb-6">Risk Level Distribution</h2>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={riskDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {riskDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex justify-center gap-6 mt-4">
                {riskDistribution.map((item, index) => (
                  <div key={index} className="flex items-center">
                    <div className="w-4 h-4 rounded-full mr-2" style={{ backgroundColor: item.color }}></div>
                    <span className="text-sm text-gray-600">{item.name}: {item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Hourly Distribution */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <h2 className="text-xl font-bold text-gray-800 mb-6">Hourly Activity Distribution</h2>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="hour" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '12px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                  }}
                />
                <Bar dataKey="count" fill="url(#colorGradient)" radius={[8, 8, 0, 0]} />
                <defs>
                  <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" />
                    <stop offset="100%" stopColor="#06b6d4" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}