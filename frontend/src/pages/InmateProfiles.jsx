// src/pages/InmateProfiles.jsx
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, User, MapPin, Calendar, AlertTriangle, Plus, Eye, Edit, Trash2,
  Shield, Menu, X, Monitor, Video, Camera, BarChart3, Upload, LogOut, Clock, Users,
  ChevronDown, ChevronRight, UserCircle, Save
} from 'lucide-react';

// Use relative paths - Vite proxy handles routing to backend

export default function InmateProfiles() {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [inmates, setInmates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  // View/Edit/Delete modal state
  const [selectedInmate, setSelectedInmate] = useState(null);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [saving, setSaving] = useState(false);

  // Add inmate form state
  const [addForm, setAddForm] = useState({
    name: '',
    age: '',
    crime: '',
    riskLevel: 'Medium',
    location: '',
    status: 'Incarcerated'
  });
  const [addMugshot, setAddMugshot] = useState(null);
  const [addPreview, setAddPreview] = useState(null);

  // Grouping state
  const [groupByRegistrant, setGroupByRegistrant] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState({});

  useEffect(() => {
    const init = async () => {
      try {
        // Check auth
        const meRes = await fetch("/auth/api/me", {
          credentials: 'include'
        });

        if (meRes.status === 401) {
          navigate('/login');
          return;
        }

        const meData = await meRes.json();
        setMe(meData);

        // Fetch inmates
        await fetchInmates();
      } catch (err) {
        console.error(err);
        setError('Failed to load inmates');
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate]);

  const fetchInmates = async () => {
    try {
      const res = await fetch("/admin/api/inmates", {
        credentials: 'include'
      });

      if (res.ok) {
        const data = await res.json();
        setInmates(data.inmates || []);
      } else {
        console.error('Failed to fetch inmates:', res.status);
        setError('Failed to load inmates data');
      }
    } catch (err) {
      console.error('Error fetching inmates:', err);
      setError('Failed to connect to server');
    }
  };

  const handleLogout = async () => {
    try {
      await fetch("/auth/api/logout", {
        method: 'POST',
        credentials: 'include'
      });
    } finally {
      window.location.href = '/login';
    }
  };

  // View modal handler
  const handleView = (inmate) => {
    setSelectedInmate(inmate);
    setViewModalOpen(true);
  };

  // Edit modal handler
  const handleEdit = (inmate) => {
    setSelectedInmate(inmate);
    setEditForm({
      name: inmate.name || '',
      age: inmate.age || '',
      status: inmate.status || 'Incarcerated',
      location: inmate.location || '',
      crime: inmate.crime || '',
      riskLevel: inmate.riskLevel || 'Medium'
    });
    setEditModalOpen(true);
  };

  // Save edit handler
  const handleSaveEdit = async () => {
    if (!selectedInmate) return;
    setSaving(true);

    try {
      const res = await fetch(`/admin/api/inmates/${selectedInmate.db_id}`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm)
      });

      if (res.ok) {
        await fetchInmates();
        setEditModalOpen(false);
        setSelectedInmate(null);
      } else {
        const data = await res.json();
        setError(data.error || 'Failed to update inmate');
      }
    } catch (err) {
      console.error('Error updating inmate:', err);
      setError('Failed to update inmate');
    } finally {
      setSaving(false);
    }
  };

  // Delete modal handler
  const handleDelete = (inmate) => {
    setSelectedInmate(inmate);
    setDeleteModalOpen(true);
  };

  // Confirm delete handler
  const handleConfirmDelete = async () => {
    if (!selectedInmate) return;
    setSaving(true);

    try {
      const res = await fetch(`/admin/api/inmates/${selectedInmate.db_id}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (res.ok) {
        setInmates(prev => prev.filter(i => i.db_id !== selectedInmate.db_id));
        setDeleteModalOpen(false);
        setSelectedInmate(null);
      } else {
        const data = await res.json();
        setError(data.error || 'Failed to delete inmate');
      }
    } catch (err) {
      console.error('Error deleting inmate:', err);
      setError('Failed to delete inmate');
    } finally {
      setSaving(false);
    }
  };

  // Toggle group expansion
  const toggleGroup = (groupKey) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupKey]: !prev[groupKey]
    }));
  };

  // Handle mugshot file selection for add modal
  const handleMugshotChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setAddMugshot(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setAddPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  // Handle add inmate submission
  const handleAddInmate = async () => {
    if (!addForm.name || !addMugshot) {
      setError('Name and mugshot image are required');
      return;
    }

    setSaving(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('name', addForm.name);
      formData.append('age', addForm.age);
      formData.append('crime', addForm.crime);
      formData.append('riskLevel', addForm.riskLevel);
      formData.append('location', addForm.location);
      formData.append('status', addForm.status);
      formData.append('mugshot', addMugshot);

      const res = await fetch('/admin/api/inmates', {
        method: 'POST',
        credentials: 'include',
        body: formData
      });

      const data = await res.json();

      if (res.ok) {
        await fetchInmates();
        setShowAddModal(false);
        // Reset form
        setAddForm({
          name: '',
          age: '',
          crime: '',
          riskLevel: 'Medium',
          location: '',
          status: 'Incarcerated'
        });
        setAddMugshot(null);
        setAddPreview(null);
      } else {
        setError(data.error || 'Failed to add inmate');
      }
    } catch (err) {
      console.error('Error adding inmate:', err);
      setError('Failed to add inmate');
    } finally {
      setSaving(false);
    }
  };

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
    const matchesSearch = inmate.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         inmate.id?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterStatus === 'all' || inmate.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  // Group inmates by registrant
  const groupedInmates = useMemo(() => {
    if (!groupByRegistrant) return null;

    const groups = {};
    filteredInmates.forEach(inmate => {
      // Use registrantName, fallback to username from email, then 'Unassigned'
      const displayName = inmate.registrantName ||
        (inmate.registrantEmail ? inmate.registrantEmail.split('@')[0] : null) ||
        'Unassigned';
      const key = inmate.registrantEmail || 'Unassigned';

      if (!groups[key]) {
        groups[key] = {
          registrantEmail: inmate.registrantEmail,
          registrantName: displayName,
          inmates: []
        };
      }
      groups[key].inmates.push(inmate);
    });

    return Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0]));
  }, [filteredInmates, groupByRegistrant]);

  const stats = {
    total: inmates.length,
    escaped: inmates.filter(i => i.status === 'Escaped').length,
    incarcerated: inmates.filter(i => i.status === 'Incarcerated').length,
    released: inmates.filter(i => i.status === 'Released').length
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center">
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

        {/* Menu */}
        {menuOpen && (
          <div className="mb-6">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-3 sm:p-4">
              <nav className="flex flex-col sm:flex-row sm:flex-wrap gap-2 text-sm text-gray-700">
                <a href={me?.is_admin ? "/admin/dashboard" : "/dashboard"} className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Monitor className="w-4 h-4 mr-2 text-blue-500" />Dashboard
                </a>
                <a href="/admin/live" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Video className="w-4 h-4 mr-2 text-purple-500" />Live Monitoring
                </a>
                <a href="/admin/upload" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                  <Camera className="w-4 h-4 mr-2 text-indigo-500" />Upload Recognition
                </a>
                <a href="/admin/inmates" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 bg-blue-50">
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
                {me?.is_admin && (
                  <a href="/admin/users" className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50">
                    <Shield className="w-4 h-4 mr-2 text-gray-700" />Manage Users
                  </a>
                )}
                <button onClick={handleLogout} className="flex items-center px-3 py-2 rounded-xl hover:bg-gray-50 sm:ml-auto text-left">
                  <LogOut className="w-4 h-4 mr-2 text-red-500" />Logout
                </button>
              </nav>
            </div>
          </div>
        )}

        {error && <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">{error}</div>}

        {/* Header Section */}
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

              <div className="flex gap-2 flex-wrap">
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
                <button
                  onClick={() => setGroupByRegistrant(!groupByRegistrant)}
                  className={`px-4 py-2.5 rounded-lg font-medium text-sm transition-all flex items-center gap-2 ${
                    groupByRegistrant
                      ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-md'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <UserCircle className="w-4 h-4" />
                  Group by Account
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Inmates Display */}
        {groupByRegistrant && groupedInmates ? (
          // GROUPED VIEW - Collapsible Folders by Registrant
          <div className="space-y-4">
            {groupedInmates.length === 0 ? (
              <div className="bg-white rounded-xl p-12 text-center shadow-md border border-gray-100">
                <User className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500 text-lg">No inmates found matching your criteria</p>
              </div>
            ) : (
              groupedInmates.map(([groupKey, group]) => (
                <div key={groupKey} className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                  {/* Folder Header - Clickable */}
                  <button
                    onClick={() => toggleGroup(groupKey)}
                    className="w-full p-4 flex items-center justify-between hover:bg-gray-50 transition"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center shadow">
                        <UserCircle className="w-6 h-6 text-white" />
                      </div>
                      <div className="text-left">
                        <h3 className="font-semibold text-gray-800">{group.registrantName || groupKey}</h3>
                        <p className="text-sm text-gray-500">{group.inmates.length} inmate{group.inmates.length !== 1 ? 's' : ''}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded-full font-medium">
                        {group.inmates.length}
                      </span>
                      {expandedGroups[groupKey] ? (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-gray-400" />
                      )}
                    </div>
                  </button>

                  {/* Collapsible Content */}
                  {expandedGroups[groupKey] && (
                    <div className="p-4 pt-0 border-t border-gray-100">
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
                        {group.inmates.map(inmate => (
                          <div key={inmate.id} className="bg-gray-50 rounded-xl shadow hover:shadow-md transition-all border border-gray-100 overflow-hidden">
                            {/* Compact Header with status */}
                            <div className="relative h-20 bg-gradient-to-br from-blue-500 to-cyan-500 p-3">
                              <div className={`absolute top-2 right-2 px-2 py-0.5 ${getStatusColor(inmate.status)} text-white text-xs font-bold rounded-full`}>
                                {inmate.status}
                              </div>
                            </div>

                            {/* Profile Image */}
                            <div className="relative px-4 -mt-10">
                              <div className="w-20 h-20 mx-auto rounded-full border-3 border-white shadow-lg overflow-hidden bg-gray-200">
                                {inmate.mugshot ? (
                                  <img src={inmate.mugshot} alt={inmate.name} className="w-full h-full object-cover" />
                                ) : (
                                  <div className="w-full h-full flex items-center justify-center">
                                    <User className="w-10 h-10 text-gray-400" />
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* Inmate Details */}
                            <div className="p-4 pt-2">
                              <div className="text-center mb-3">
                                <h3 className="text-lg font-bold text-gray-800">{inmate.name}</h3>
                                <p className="text-xs text-gray-500">{inmate.id}</p>
                              </div>

                              <div className="space-y-1.5 mb-3 text-xs">
                                <div className="flex items-center text-gray-600">
                                  <MapPin className="w-3 h-3 mr-1.5 text-gray-400" />
                                  <span className="truncate">{inmate.location}</span>
                                </div>
                                <div className="flex items-center text-gray-600">
                                  <AlertTriangle className="w-3 h-3 mr-1.5 text-gray-400" />
                                  <span className="truncate">{inmate.crime}</span>
                                </div>
                              </div>

                              <span className={`inline-block px-2 py-0.5 text-xs font-bold rounded-full border mb-3 ${getRiskColor(inmate.riskLevel)}`}>
                                {inmate.riskLevel} Risk
                              </span>

                              {/* Actions */}
                              <div className="flex gap-1.5">
                                <button onClick={() => handleView(inmate)} className="flex-1 px-2 py-1.5 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition-all font-medium text-xs flex items-center justify-center">
                                  <Eye className="w-3 h-3 mr-1" /> View
                                </button>
                                {/* Only show edit if admin OR registrant */}
                                {(me?.is_admin || inmate.registered_by === me?.id) && (
                                  <button onClick={() => handleEdit(inmate)} className="px-2 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-all">
                                    <Edit className="w-3 h-3" />
                                  </button>
                                )}
                                {me?.is_admin && (
                                  <button onClick={() => handleDelete(inmate)} className="px-2 py-1.5 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-all">
                                    <Trash2 className="w-3 h-3" />
                                  </button>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        ) : (
          // FLAT VIEW - Original Grid
          <>
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
                      {inmate.mugshot ? (
                        <img
                          src={inmate.mugshot}
                          alt={inmate.name}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'flex';
                          }}
                        />
                      ) : null}
                      <div className={`w-full h-full items-center justify-center ${inmate.mugshot ? 'hidden' : 'flex'}`}>
                        <User className="w-16 h-16 text-gray-400" />
                      </div>
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
                      <button
                        onClick={() => handleView(inmate)}
                        className="flex-1 px-3 py-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition-all font-medium text-sm flex items-center justify-center"
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        View
                      </button>
                      {/* Only show edit if admin OR registrant */}
                      {(me?.is_admin || inmate.registered_by === me?.id) && (
                        <button
                          onClick={() => handleEdit(inmate)}
                          className="px-3 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-all"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                      )}
                      {me?.is_admin && (
                        <button
                          onClick={() => handleDelete(inmate)}
                          className="px-3 py-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-all"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
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
          </>
        )}
      </div>

      {/* View Modal */}
      {viewModalOpen && selectedInmate && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-xl font-bold text-gray-800">Inmate Details</h3>
              <button
                onClick={() => { setViewModalOpen(false); setSelectedInmate(null); }}
                className="p-2 hover:bg-gray-100 rounded-lg transition"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6">
              <div className="flex flex-col md:flex-row gap-6">
                <div className="flex-shrink-0">
                  <div className="w-40 h-40 rounded-xl overflow-hidden bg-gray-200">
                    {selectedInmate.mugshot ? (
                      <img src={selectedInmate.mugshot} alt={selectedInmate.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <User className="w-20 h-20 text-gray-400" />
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex-1 space-y-4">
                  <div>
                    <h4 className="text-2xl font-bold text-gray-800">{selectedInmate.name}</h4>
                    <p className="text-gray-500">ID: {selectedInmate.id}</p>
                  </div>
                  <div className="flex gap-2">
                    <span className={`px-3 py-1 text-sm font-medium rounded-full ${getStatusColor(selectedInmate.status)} text-white`}>
                      {selectedInmate.status}
                    </span>
                    <span className={`px-3 py-1 text-sm font-medium rounded-full border ${getRiskColor(selectedInmate.riskLevel)}`}>
                      {selectedInmate.riskLevel} Risk
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">Age</p>
                      <p className="font-medium text-gray-800">{selectedInmate.age} years old</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Location</p>
                      <p className="font-medium text-gray-800">{selectedInmate.location || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Crime</p>
                      <p className="font-medium text-gray-800">{selectedInmate.crime || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Last Seen</p>
                      <p className="font-medium text-gray-800">{selectedInmate.lastSeen}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Sentence Start</p>
                      <p className="font-medium text-gray-800">{selectedInmate.sentenceStart ? new Date(selectedInmate.sentenceStart).toLocaleDateString() : 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Expected Release</p>
                      <p className="font-medium text-gray-800">{selectedInmate.expectedRelease || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Registered By</p>
                      <p className="font-medium text-gray-800">{selectedInmate.registrantEmail || 'Unknown'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Created At</p>
                      <p className="font-medium text-gray-800">{selectedInmate.createdAt ? new Date(selectedInmate.createdAt).toLocaleDateString() : 'N/A'}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="p-6 border-t border-gray-100 flex justify-end gap-3">
              <button
                onClick={() => { setViewModalOpen(false); handleEdit(selectedInmate); }}
                className="px-4 py-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition font-medium flex items-center gap-2"
              >
                <Edit className="w-4 h-4" />
                Edit
              </button>
              <button
                onClick={() => { setViewModalOpen(false); setSelectedInmate(null); }}
                className="px-4 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editModalOpen && selectedInmate && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-xl font-bold text-gray-800">Edit Inmate</h3>
              <button
                onClick={() => { setEditModalOpen(false); setSelectedInmate(null); }}
                className="p-2 hover:bg-gray-100 rounded-lg transition"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Age</label>
                  <input
                    type="number"
                    value={editForm.age}
                    onChange={(e) => setEditForm({ ...editForm, age: parseInt(e.target.value) || '' })}
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                  <select
                    value={editForm.status}
                    onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                  >
                    <option value="Incarcerated">Incarcerated</option>
                    <option value="Released">Released</option>
                    <option value="Escaped">Escaped</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
                <input
                  type="text"
                  value={editForm.location}
                  onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Crime</label>
                <input
                  type="text"
                  value={editForm.crime}
                  onChange={(e) => setEditForm({ ...editForm, crime: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Risk Level</label>
                <select
                  value={editForm.riskLevel}
                  onChange={(e) => setEditForm({ ...editForm, riskLevel: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                </select>
              </div>
            </div>
            <div className="p-6 border-t border-gray-100 flex justify-end gap-3">
              <button
                onClick={() => { setEditModalOpen(false); setSelectedInmate(null); }}
                className="px-4 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                disabled={saving}
                className="px-4 py-2 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-lg hover:from-blue-600 hover:to-cyan-600 transition font-medium flex items-center gap-2 disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && selectedInmate && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full">
            <div className="p-6">
              <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-red-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 text-center mb-2">Delete Inmate</h3>
              <p className="text-gray-600 text-center mb-6">
                Are you sure you want to delete <strong>{selectedInmate.name}</strong>? This action cannot be undone.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => { setDeleteModalOpen(false); setSelectedInmate(null); }}
                  className="flex-1 px-4 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmDelete}
                  disabled={saving}
                  className="flex-1 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition font-medium disabled:opacity-50"
                >
                  {saving ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Inmate Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-xl font-bold text-gray-800">Add New Inmate</h3>
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setAddForm({ name: '', age: '', crime: '', riskLevel: 'Medium', location: '', status: 'Incarcerated' });
                  setAddMugshot(null);
                  setAddPreview(null);
                }}
                className="p-2 hover:bg-gray-100 rounded-lg transition"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              {/* Mugshot Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Mugshot Photo *</label>
                <div className="flex items-center gap-4">
                  <div className="w-24 h-24 rounded-xl overflow-hidden bg-gray-100 border-2 border-dashed border-gray-300 flex items-center justify-center">
                    {addPreview ? (
                      <img src={addPreview} alt="Preview" className="w-full h-full object-cover" />
                    ) : (
                      <User className="w-10 h-10 text-gray-400" />
                    )}
                  </div>
                  <div className="flex-1">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleMugshotChange}
                      className="hidden"
                      id="mugshot-upload"
                    />
                    <label
                      htmlFor="mugshot-upload"
                      className="inline-flex items-center px-4 py-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition cursor-pointer font-medium"
                    >
                      <Upload className="w-4 h-4 mr-2" />
                      Choose Photo
                    </label>
                    <p className="text-xs text-gray-500 mt-1">JPG, PNG up to 5MB</p>
                  </div>
                </div>
              </div>

              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
                <input
                  type="text"
                  value={addForm.name}
                  onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
                  placeholder="Enter inmate's full name"
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>

              {/* Age and Status */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Age</label>
                  <input
                    type="number"
                    value={addForm.age}
                    onChange={(e) => setAddForm({ ...addForm, age: e.target.value })}
                    placeholder="Age"
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                  <select
                    value={addForm.status}
                    onChange={(e) => setAddForm({ ...addForm, status: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                  >
                    <option value="Incarcerated">Incarcerated</option>
                    <option value="Released">Released</option>
                    <option value="Escaped">Escaped</option>
                  </select>
                </div>
              </div>

              {/* Location */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Location/Facility</label>
                <input
                  type="text"
                  value={addForm.location}
                  onChange={(e) => setAddForm({ ...addForm, location: e.target.value })}
                  placeholder="e.g., Central Prison, Block A"
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>

              {/* Crime */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Crime/Offense</label>
                <input
                  type="text"
                  value={addForm.crime}
                  onChange={(e) => setAddForm({ ...addForm, crime: e.target.value })}
                  placeholder="e.g., Armed Robbery"
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>

              {/* Risk Level */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Risk Level</label>
                <select
                  value={addForm.riskLevel}
                  onChange={(e) => setAddForm({ ...addForm, riskLevel: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                </select>
              </div>
            </div>
            <div className="p-6 border-t border-gray-100 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setAddForm({ name: '', age: '', crime: '', riskLevel: 'Medium', location: '', status: 'Incarcerated' });
                  setAddMugshot(null);
                  setAddPreview(null);
                }}
                className="px-4 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleAddInmate}
                disabled={saving || !addForm.name || !addMugshot}
                className="px-4 py-2 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-lg hover:from-blue-600 hover:to-cyan-600 transition font-medium flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Plus className="w-4 h-4" />
                {saving ? 'Adding...' : 'Add Inmate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}