// src/pages/ManageUsers.jsx
import { useState, useEffect } from 'react';
import {
  Users,
  Plus,
  Edit,
  Trash2,
  Power,
  Search,
  Shield,
  UserCheck,
  UserX,
  Mail,
  Menu,
  X,
  Monitor,
  Video,
  Camera,
  AlertTriangle,
  BarChart3,
  Upload,
  LogOut,
  Clock,
  Eye,
  EyeOff,
} from 'lucide-react';

const BACKEND_BASE_URL = 'http://127.0.0.1:5000';

export default function ManageUsers() {
  const [users, setUsers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    is_admin: false,
  });
  const [menuOpen, setMenuOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Load users on mount
  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError('');

      const res = await fetch(`${BACKEND_BASE_URL}/admin/api/users`, {
        method: 'GET',
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });

      if (!res.ok) {
        let msg = 'Failed to fetch users';
        try {
          const data = await res.json();
          msg = data.error || data.message || msg;
        } catch (_) {
          // ignore JSON parse errors
        }
        throw new Error(msg);
      }

      const data = await res.json();
      setUsers(data.users || []);
    } catch (err) {
      setError(err.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const addUser = async () => {
    if (!formData.name || !formData.email || !formData.password) {
      alert('Please fill in all fields');
      return;
    }
    try {
      const res = await fetch(`${BACKEND_BASE_URL}/admin/api/users`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        let msg = 'Failed to create user';
        try {
          const data = await res.json();
          msg = data.error || data.message || msg;
        } catch (_) {}
        throw new Error(msg);
      }

      alert('User created successfully!');
      setFormData({
        name: '',
        email: '',
        password: '',
        is_admin: false,
      });
      setShowAddModal(false);
      fetchUsers();
    } catch (err) {
      alert(err.message || 'Failed to create user');
    }
  };

  const updateUser = async () => {
    if (!formData.name || !formData.email) {
      alert('Please fill in required fields');
      return;
    }
    try {
      const payload = {
        name: formData.name,
        email: formData.email,
        is_admin: formData.is_admin,
      };
      if (formData.password) {
        payload.password = formData.password;
      }

      const res = await fetch(
        `${BACKEND_BASE_URL}/admin/api/users/${editingUser.id}`,
        {
          method: 'PUT',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }
      );

      if (!res.ok) {
        let msg = 'Failed to update user';
        try {
          const data = await res.json();
          msg = data.error || data.message || msg;
        } catch (_) {}
        throw new Error(msg);
      }

      alert('User updated successfully!');
      closeModals();
      fetchUsers();
    } catch (err) {
      alert(err.message || 'Failed to update user');
    }
  };

  const toggleStatus = async (userId, currentStatus) => {
    if (!window.confirm(`${currentStatus ? 'Suspend' : 'Activate'} this user?`))
      return;

    try {
      const res = await fetch(
        `${BACKEND_BASE_URL}/admin/api/users/${userId}/toggle-status`,
        {
          method: 'PUT',
          credentials: 'include',
        }
      );

      if (!res.ok) {
        let msg = 'Failed to toggle status';
        try {
          const data = await res.json();
          msg = data.error || data.message || msg;
        } catch (_) {}
        throw new Error(msg);
      }

      fetchUsers();
    } catch (err) {
      alert(err.message || 'Failed to toggle status');
    }
  };

  const deleteUser = async (userId) => {
    if (!window.confirm('Delete this user? This cannot be undone.')) return;
    try {
      const res = await fetch(
        `${BACKEND_BASE_URL}/admin/api/users/${userId}`,
        {
          method: 'DELETE',
          credentials: 'include',
        }
      );

      if (!res.ok) {
        let msg = 'Failed to delete user';
        try {
          const data = await res.json();
          msg = data.error || data.message || msg;
        } catch (_) {}
        throw new Error(msg);
      }

      alert('User deleted successfully!');
      fetchUsers();
    } catch (err) {
      alert(err.message || 'Failed to delete user');
    }
  };

  const openEditModal = (user) => {
    setEditingUser(user);
    setFormData({
      name: user.name || '',
      email: user.email || '',
      password: '',
      is_admin: !!user.is_admin,
    });
    setShowEditModal(true);
  };

  const closeModals = () => {
    setShowAddModal(false);
    setShowEditModal(false);
    setEditingUser(null);
    setFormData({
      name: '',
      email: '',
      password: '',
      is_admin: false,
    });
    setShowPassword(false);
  };

  const formatLastLogin = (lastLogin) => {
    if (!lastLogin) return 'Never';
    const date = new Date(lastLogin);
    const diffMs = new Date() - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60)
      return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24)
      return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7)
      return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
  };

  const filteredUsers = users.filter(
    (u) =>
      u.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const stats = {
    total: users.length,
    active: users.filter((u) => u.is_active).length,
    suspended: users.filter((u) => !u.is_active).length,
    admins: users.filter((u) => u.is_admin).length,
  };

  if (loading && users.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
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
              <h1 className="text-xl md:text-2xl font-bold text-gray-800">
                Heimdall Admin
              </h1>
              <p className="text-xs md:text-sm text-gray-500">
                User Management
              </p>
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
              onClick={() => setMenuOpen(!menuOpen)}
              className="w-10 h-10 rounded-xl bg-white shadow-md border border-gray-100 hover:bg-gray-50 flex items-center justify-center"
            >
              {menuOpen ? (
                <X className="w-5 h-5" />
              ) : (
                <Menu className="w-5 h-5" />
              )}
            </button>
          </div>
        </header>

        {/* Hamburger menu */}
        {menuOpen && (
          <div className="mb-6 bg-white rounded-2xl shadow-lg border border-gray-100 p-3 sm:p-4">
            <nav className="flex flex-col sm:flex-row sm:flex-wrap gap-2 text-sm">
              <a
                href="/admin/dashboard"
                className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
              >
                <Monitor className="w-4 h-4 mr-2 text-blue-500" />
                Dashboard
              </a>
              <a
                href="/admin/live"
                className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
              >
                <Video className="w-4 h-4 mr-2 text-purple-500" />
                Live Monitoring
              </a>
              <a
                href="/admin/upload"
                className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
              >
                <Camera className="w-4 h-4 mr-2 text-indigo-500" />
                Upload Recognition
              </a>
              <a
                href="/admin/inmates"
                className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
              >
                <Users className="w-4 h-4 mr-2 text-emerald-500" />
                Inmate Profiles
              </a>
              <a
                href="/admin/alerts"
                className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
              >
                <AlertTriangle className="w-4 h-4 mr-2 text-orange-500" />
                Alerts & Logs
              </a>
              <a
                href="/admin/analytics"
                className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
              >
                <BarChart3 className="w-4 h-4 mr-2 text-cyan-500" />
                Analytics
              </a>
              <a
                href="/admin/cameras"
                className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50"
              >
                <Camera className="w-4 h-4 mr-2 text-blue-500" />
                Manage Cameras
              </a>
              <a
                href="/admin/users"
                className="flex items-center px-3 py-2 rounded-xl bg-blue-50"
              >
                <Shield className="w-4 h-4 mr-2" />
                Manage Users
              </a>
              <a
                href={`${BACKEND_BASE_URL}/auth/logout`}
                className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 sm:ml-auto"
              >
                <LogOut className="w-4 h-4 mr-2 text-red-500" />
                Logout
              </a>
            </nav>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Heading + add button */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-3xl font-bold text-gray-800 mb-2">
                User Management
              </h2>
              <p className="text-gray-600 flex items-center">
                <Users className="w-4 h-4 mr-2" />
                Manage system users and permissions
              </p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-semibold rounded-xl shadow-lg"
            >
              <Plus className="w-5 h-5 mr-2" />
              Add User
            </button>
          </div>

          {/* Stats cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {[
              { label: 'Total Users', value: stats.total, icon: Users },
              { label: 'Active', value: stats.active, icon: UserCheck },
              { label: 'Suspended', value: stats.suspended, icon: UserX },
              { label: 'Administrators', value: stats.admins, icon: Shield },
            ].map(({ label, value, icon: Icon }) => (
              <div
                key={label}
                className="bg-white rounded-xl p-4 shadow-md border border-gray-100"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-500 text-sm font-medium">
                      {label}
                    </p>
                    <p className="text-2xl font-bold text-gray-800">
                      {value}
                    </p>
                  </div>
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <Icon className="w-6 h-6 text-blue-600" />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Search bar */}
          <div className="bg-white rounded-xl shadow-md border border-gray-100 p-4 mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by name or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
          </div>
        </div>

        {/* Users table */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {[
                    'User',
                    'Email',
                    'Role',
                    'Status',
                    'Last Login',
                    'Actions',
                  ].map((h) => (
                    <th
                      key={h}
                      className="px-6 py-4 text-left text-sm font-semibold text-gray-700"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white font-bold text-sm mr-3">
                          {user.name
                            ?.split(' ')
                            .map((n) => n[0])
                            .join('') || '??'}
                        </div>
                        <span className="font-medium">{user.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center text-gray-600">
                        <Mail className="w-4 h-4 mr-2 text-gray-400" />
                        <span className="text-sm">{user.email}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {user.is_admin ? (
                        <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-bold flex items-center w-fit">
                          <Shield className="w-3 h-3 mr-1" />
                          Admin
                        </span>
                      ) : (
                        <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs">
                          User
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div
                          className={`w-2 h-2 rounded-full mr-2 ${
                            user.is_active
                              ? 'bg-green-500 animate-pulse'
                              : 'bg-red-500'
                          }`}
                        />
                        <span
                          className={`text-sm font-medium ${
                            user.is_active
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {user.is_active ? 'Active' : 'Suspended'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-600">
                        {formatLastLogin(user.last_login)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() =>
                            toggleStatus(user.id, user.is_active)
                          }
                          className={`p-2 rounded-lg ${
                            user.is_active
                              ? 'bg-orange-100 text-orange-600'
                              : 'bg-green-100 text-green-600'
                          }`}
                        >
                          <Power className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => openEditModal(user)}
                          className="p-2 bg-blue-100 text-blue-600 rounded-lg"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => deleteUser(user.id)}
                          className="p-2 bg-red-100 text-red-600 rounded-lg"
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

          {filteredUsers.length === 0 && (
            <div className="text-center py-12">
              <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No users found</p>
            </div>
          )}
        </div>

        {/* Add / Edit modal */}
        {(showAddModal || showEditModal) && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
              <h2 className="text-2xl font-bold mb-6">
                {showEditModal ? 'Edit User' : 'Add New User'}
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold mb-2">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    placeholder="John Doe"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        name: e.target.value,
                      })
                    }
                    className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-2">
                    Email *
                  </label>
                  <input
                    type="email"
                    placeholder="john@heimdall.com"
                    value={formData.email}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        email: e.target.value,
                      })
                    }
                    className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-2">
                    Password{' '}
                    {showEditModal &&
                      '(leave blank to keep current)'}
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Enter password"
                      value={formData.password}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          password: e.target.value,
                        })
                      }
                      className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-400"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2"
                    >
                      {showPassword ? (
                        <EyeOff className="w-5 h-5" />
                      ) : (
                        <Eye className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_admin}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        is_admin: e.target.checked,
                      })
                    }
                    className="w-5 h-5 rounded"
                  />
                  <span className="ml-3 text-sm font-medium">
                    Grant Administrator Privileges
                  </span>
                </label>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={closeModals}
                  className="flex-1 px-4 py-3 bg-gray-100 rounded-xl font-semibold"
                >
                  Cancel
                </button>
                <button
                  onClick={showEditModal ? updateUser : addUser}
                  className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-semibold"
                >
                  {showEditModal ? 'Update' : 'Add'} User
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}