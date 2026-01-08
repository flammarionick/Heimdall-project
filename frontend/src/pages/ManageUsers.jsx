// ============================================================
// 2. ManageUsers.jsx - COMPLETE WITH ALL FUNCTIONALITY
// ============================================================
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Users, Search, Plus, Edit, Trash2, Power, Shield,
  UserCheck, UserX, RefreshCw, AlertCircle, X, Eye, EyeOff,
  Menu, LogOut, Clock, Monitor, Video, Camera, AlertTriangle, BarChart3
} from "lucide-react";

// Use relative paths - Vite proxy handles routing to backend
const API_BASE = "";

export default function ManageUsers() {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    name: "", email: "", password: "", is_admin: false
  });

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE}/auth/api/logout`, {
        method: "POST",
        credentials: "include"
      });
    } finally {
      window.location.href = "/login";
    }
  };

  const fetchMe = async () => {
    const r = await fetch(`${API_BASE}/auth/api/me`, { credentials: "include" });
    if (r.status === 401) return null;
    if (!r.ok) throw new Error("Failed to load session");
    return r.json();
  };

  const fetchUsers = async () => {
    const r = await fetch(`${API_BASE}/admin/api/users`, { credentials: "include" });
    if (r.status === 401) throw new Error("UNAUTHORIZED");
    if (r.status === 403) throw new Error("FORBIDDEN");
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      throw new Error(data.error || "Failed to load users");
    }
    const data = await r.json();
    return data.users || [];
  };

  const refresh = async () => {
    setError("");
    setLoading(true);
    try {
      const session = await fetchMe();
      if (!session) {
        navigate("/login");
        return;
      }
      if (!session.is_admin) {
        navigate("/dashboard");
        return;
      }
      setMe(session);
      const list = await fetchUsers();
      setUsers(list);
    } catch (e) {
      const msg = String(e?.message || e);
      if (msg === "UNAUTHORIZED") {
        navigate("/login");
        return;
      }
      if (msg === "FORBIDDEN") {
        setError("Forbidden – admin only");
        return;
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const openAddModal = () => {
    setFormData({ name: "", email: "", password: "", is_admin: false });
    setShowPassword(false);
    setShowAddModal(true);
  };

  const openEditModal = (user) => {
    setEditingUser(user);
    setFormData({
      name: user.name,
      email: user.email,
      password: "",
      is_admin: user.is_admin
    });
    setShowPassword(false);
    setShowEditModal(true);
  };

  const closeModals = () => {
    setShowAddModal(false);
    setShowEditModal(false);
    setEditingUser(null);
    setFormData({ name: "", email: "", password: "", is_admin: false });
    setShowPassword(false);
  };

  const onCreateUser = async () => {
    if (!formData.name || !formData.email || !formData.password) {
      alert("Please fill in all required fields");
      return;
    }
    setActionLoading(true);
    setError("");
    try {
      const r = await fetch(`${API_BASE}/admin/api/users`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error || "Failed to create user");
      closeModals();
      await refresh();
    } catch (e) {
      setError(String(e?.message || e));
    } finally {
      setActionLoading(false);
    }
  };

  const onUpdateUser = async () => {
    if (!formData.name || !formData.email) {
      alert("Please fill in required fields");
      return;
    }
    setActionLoading(true);
    setError("");
    try {
      const payload = {
        name: formData.name,
        email: formData.email,
        is_admin: formData.is_admin
      };
      if (formData.password) payload.password = formData.password;

      const r = await fetch(`${API_BASE}/admin/api/users/${editingUser.id}`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error || "Failed to update user");
      closeModals();
      await refresh();
    } catch (e) {
      setError(String(e?.message || e));
    } finally {
      setActionLoading(false);
    }
  };

  const onToggleStatus = async (userId) => {
    setActionLoading(true);
    setError("");
    try {
      const r = await fetch(`${API_BASE}/admin/api/users/${userId}/toggle-status`, {
        method: "PUT",
        credentials: "include",
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error || "Failed to toggle status");
      await refresh();
    } catch (e) {
      setError(String(e?.message || e));
    } finally {
      setActionLoading(false);
    }
  };

  const onDeleteUser = async (userId) => {
    if (!confirm("Delete this user? This cannot be undone.")) return;
    setActionLoading(true);
    setError("");
    try {
      const r = await fetch(`${API_BASE}/admin/api/users/${userId}`, {
        method: "DELETE",
        credentials: "include",
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error || "Failed to delete user");
      await refresh();
    } catch (e) {
      setError(String(e?.message || e));
    } finally {
      setActionLoading(false);
    }
  };

  const filteredUsers = users.filter(u =>
    u.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const stats = {
    total: users.length,
    active: users.filter(u => u.is_active).length,
    suspended: users.filter(u => !u.is_active).length,
    admins: users.filter(u => u.is_admin).length
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

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
              <p className="text-xs md:text-sm text-gray-500">User Management</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center bg-white rounded-xl px-3 py-2 shadow">
              <Clock className="w-4 h-4 text-blue-500 mr-2" />
              <span className="text-xs md:text-sm font-medium text-gray-700">
                {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
              </span>
            </div>
            <button onClick={() => setMenuOpen(!menuOpen)} className="w-10 h-10 rounded-xl bg-white shadow-md border hover:bg-gray-50 flex items-center justify-center">
              {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </header>

        {/* Menu */}
        {menuOpen && (
          <div className="mb-6 bg-white rounded-2xl shadow-lg border p-3 sm:p-4">
            <nav className="flex flex-col sm:flex-row sm:flex-wrap gap-2 text-sm">
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
              <a href="/admin/cameras" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                <Camera className="w-4 h-4 mr-2 text-blue-500" />Manage Cameras
              </a>
              <a href="/admin/users" className="flex items-center px-3 py-2 rounded-xl bg-blue-50">
                <Shield className="w-4 h-4 mr-2" />Manage Users
              </a>
              <button onClick={handleLogout} className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 sm:ml-auto text-left">
                <LogOut className="w-4 h-4 mr-2 text-red-500" />Logout
              </button>
            </nav>
          </div>
        )}

        {error && <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">{error}</div>}

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Total', value: stats.total, icon: Users, color: 'blue' },
            { label: 'Active', value: stats.active, icon: UserCheck, color: 'green' },
            { label: 'Suspended', value: stats.suspended, icon: UserX, color: 'red' },
            { label: 'Admins', value: stats.admins, icon: Shield, color: 'purple' }
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="bg-white rounded-xl p-4 shadow-md border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm">{label}</p>
                  <p className="text-2xl font-bold">{value}</p>
                </div>
                <div className={`p-3 bg-${color}-100 rounded-lg`}>
                  <Icon className={`w-6 h-6 text-${color}-600`} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Search + Add */}
        <div className="bg-white rounded-xl shadow-md border p-4 mb-6 flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search users..."
              className="w-full pl-10 pr-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <button onClick={openAddModal} className="px-6 py-2.5 bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold rounded-xl shadow flex items-center gap-2">
            <Plus className="w-5 h-5" />Add User
          </button>
        </div>

        {/* Table */}
        <div className="bg-white rounded-2xl shadow-lg border overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                {['User', 'Email', 'Role', 'Status', 'Actions'].map(h => (
                  <th key={h} className="px-6 py-4 text-left text-sm font-semibold text-gray-700">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredUsers.map(u => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white font-bold mr-3">
                        {u.name?.split(' ').map(n => n[0]).join('') || '?'}
                      </div>
                      <span className="font-medium">{u.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{u.email}</td>
                  <td className="px-6 py-4">
                    {u.is_admin ? (
                      <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-bold flex items-center w-fit">
                        <Shield className="w-3 h-3 mr-1" />Admin
                      </span>
                    ) : (
                      <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs">User</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <div className={`w-2 h-2 rounded-full mr-2 ${u.is_active ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                      <span className={`text-sm font-medium ${u.is_active ? 'text-green-600' : 'text-red-600'}`}>
                        {u.is_active ? 'Active' : 'Suspended'}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => onToggleStatus(u.id)}
                        disabled={actionLoading || me?.id === u.id}
                        className={`p-2 rounded-lg ${u.is_active ? 'bg-orange-100 text-orange-600' : 'bg-green-100 text-green-600'} disabled:opacity-50`}
                      >
                        <Power className="w-4 h-4" />
                      </button>
                      <button onClick={() => openEditModal(u)} className="p-2 bg-blue-100 text-blue-600 rounded-lg">
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => onDeleteUser(u.id)}
                        disabled={actionLoading || me?.id === u.id}
                        className="p-2 bg-red-100 text-red-600 rounded-lg disabled:opacity-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredUsers.length === 0 && (
            <div className="text-center py-12">
              <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No users found</p>
            </div>
          )}
        </div>

        {/* Add/Edit Modal */}
        {(showAddModal || showEditModal) && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
              <h2 className="text-2xl font-bold mb-6">{showEditModal ? 'Edit User' : 'Add New User'}</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold mb-2">Full Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-2">Email *</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-2">
                    Password {showEditModal && "(leave blank to keep current)"}
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-400"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_admin}
                    onChange={(e) => setFormData({ ...formData, is_admin: e.target.checked })}
                    className="w-5 h-5 rounded"
                  />
                  <span className="ml-3 text-sm font-medium">Grant Administrator Privileges</span>
                </label>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={closeModals} className="flex-1 px-4 py-3 bg-gray-100 rounded-xl font-semibold">
                  Cancel
                </button>
                <button
                  onClick={showEditModal ? onUpdateUser : onCreateUser}
                  disabled={actionLoading}
                  className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-semibold disabled:opacity-50"
                >
                  {actionLoading ? 'Saving...' : showEditModal ? 'Update' : 'Create'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
    )}