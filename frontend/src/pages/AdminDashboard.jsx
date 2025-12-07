// src/pages/AdminDashboard.jsx
import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Users,
  Camera,
  AlertTriangle,
  Shield,
  TrendingUp,
  Activity,
  Clock,
  CheckCircle,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

export default function AdminDashboard() {
  const [stats, setStats] = useState({
    total_users: 0,
    active_users: 0,
    suspended_users: 0,
    total_cameras: 0,
    total_alerts: 0,
    total_inmates: 0,
    matches_over_time: [],
    inmate_status: [],
  });
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch(`${API_BASE}/admin/api/stats`, {
          method: "GET",
          credentials: "include",
          headers: {
            Accept: "application/json",
          },
        });

        const contentType = res.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
          const text = await res.text();
          throw new Error(
            `Expected JSON, got non-JSON response: ${text.slice(0, 200)}`
          );
        }

        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.error || `HTTP ${res.status}`);
        }

        setStats((prev) => ({
          ...prev,
          ...data,
        }));
        setError("");
      } catch (err) {
        console.error("Could not load stats:", err);
        setError("Could not load analytics");
      }
    }

    fetchStats();
  }, []);

  const StatCard = ({ icon: Icon, title, value, change, color, bgColor }) => (
    <div className="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all transform hover:scale-[1.02] border border-gray-100">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-xl ${bgColor}`}>
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
        {change !== undefined && (
          <div className="flex items-center text-sm">
            <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
            <span className="text-green-600 font-semibold">
              {change}%
            </span>
          </div>
        )}
      </div>
      <h3 className="text-gray-500 text-sm font-medium mb-1">{title}</h3>
      <p className="text-3xl font-bold text-gray-800">
        {(value ?? 0).toLocaleString()}
      </p>
    </div>
  );

  const COLORS = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b"];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-gray-800 mb-2">
                Admin Dashboard
              </h1>
              <p className="text-gray-600 flex items-center">
                <Activity className="w-4 h-4 mr-2" />
                Real-time security monitoring and analytics
              </p>
              {error && (
                <p className="mt-3 text-sm text-red-600 font-medium">
                  {error}
                </p>
              )}
            </div>
            <div className="flex items-center space-x-3">
              <div className="bg-white px-4 py-2 rounded-xl shadow-md flex items-center">
                <Clock className="w-4 h-4 text-blue-500 mr-2" />
                <span className="text-sm font-medium text-gray-700">
                  {new Date().toLocaleDateString("en-US", {
                    weekday: "long",
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            icon={Users}
            title="Total Users"
            value={stats.total_users}
            change={12}
            color="text-blue-600"
            bgColor="bg-blue-100"
          />
          <StatCard
            icon={CheckCircle}
            title="Active Users"
            value={stats.active_users}
            change={8}
            color="text-green-600"
            bgColor="bg-green-100"
          />
          <StatCard
            icon={Camera}
            title="Active Cameras"
            value={stats.total_cameras}
            change={5}
            color="text-purple-600"
            bgColor="bg-purple-100"
          />
          <StatCard
            icon={AlertTriangle}
            title="Total Alerts"
            value={stats.total_alerts}
            color="text-orange-600"
            bgColor="bg-orange-100"
          />
        </div>

        {/* Additional Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-gray-800">
                System Status
              </h3>
              <div className="flex items-center">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                <span className="text-sm text-green-600 font-medium">
                  Operational
                </span>
              </div>
            </div>
            <div className="space-y-4 mt-6">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Detection Accuracy</span>
                  <span className="font-semibold text-gray-800">
                    94.2%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-cyan-500 h-2 rounded-full"
                    style={{ width: "94.2%" }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">System Uptime</span>
                  <span className="font-semibold text-gray-800">
                    99.8%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full"
                    style={{ width: "99.8%" }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Response Time</span>
                  <span className="font-semibold text-gray-800">
                    0.3s
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full"
                    style={{ width: "85%" }}
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-800 mb-2">
              Quick Stats
            </h3>
            <div className="grid grid-cols-2 gap-4 mt-6">
              <div className="text-center p-4 bg-blue-50 rounded-xl">
                <Shield className="w-8 h-8 text-blue-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-800">
                  {stats.total_inmates ?? 0}
                </p>
                <p className="text-sm text-gray-600">Total Inmates</p>
              </div>
              <div className="text-center p-4 bg-red-50 rounded-xl">
                <AlertTriangle className="w-8 h-8 text-red-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-800">
                  {stats.suspended_users ?? 0}
                </p>
                <p className="text-sm text-gray-600">Suspended Users</p>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-xl col-span-2">
                <Activity className="w-8 h-8 text-green-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-800">
                  {/* Example derived metric */}
                  {stats.matches_over_time.reduce(
                    (sum, m) => sum + m.count,
                    0
                  ) || 0}
                </p>
                <p className="text-sm text-gray-600">
                  Matches (shown period)
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Line Chart */}
          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-800">
                Recognition Trends
              </h2>
              <select className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm font-medium text-gray-700 border-none focus:outline-none focus:ring-2 focus:ring-blue-400">
                <option>Last Period</option>
              </select>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={stats.matches_over_time}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#fff",
                    border: "1px solid #e5e7eb",
                    borderRadius: "12px",
                    boxShadow:
                      "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#3b82f6"
                  strokeWidth={3}
                  dot={{ fill: "#3b82f6", r: 5 }}
                  activeDot={{ r: 7 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Pie Chart */}
          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-800">
                Inmate Status Distribution
              </h2>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={stats.inmate_status}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) =>
                    `${name}: ${(percent * 100).toFixed(0)}%`
                  }
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {stats.inmate_status.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-6 mt-4">
              {stats.inmate_status.map((item, index) => (
                <div key={index} className="flex items-center">
                  <div
                    className="w-4 h-4 rounded-full mr-2"
                    style={{ backgroundColor: COLORS[index] }}
                  ></div>
                  <span className="text-sm text-gray-600">
                    {item.name}: {item.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}