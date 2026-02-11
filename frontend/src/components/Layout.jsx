// src/components/Layout.jsx
import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Video,
  Users,
  Camera,
  Bell,
  BarChart3,
  Upload,
  Settings,
  LogOut,
  Menu,
  X,
  User,
  ChevronRight,
  Zap,
  Radar
} from 'lucide-react';

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();

  // Get user info from window (passed from Flask)
  const user = window.__INITIAL_STATE__?.user || {};
  const isAdmin = user.isAdmin;

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      window.location.href = '/login';
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const navItems = [
    {
      name: 'Dashboard',
      path: isAdmin ? '/admin' : '/dashboard',
      icon: LayoutDashboard,
      adminOnly: false
    },
    {
      name: 'Live Monitoring',
      path: '/monitoring',
      icon: Video,
      adminOnly: false
    },
    {
      name: 'Inmates',
      path: '/inmates',
      icon: Users,
      adminOnly: false
    },
    {
      name: 'Cameras',
      path: '/cameras',
      icon: Camera,
      adminOnly: false
    },
    {
      name: 'Alerts & Logs',
      path: '/alerts',
      icon: Bell,
      adminOnly: false
    },
    {
      name: 'Surveillance',
      path: '/surveillance',
      icon: Radar,
      adminOnly: false
    },
    {
      name: 'Analytics',
      path: '/analytics',
      icon: BarChart3,
      adminOnly: false
    },
    {
      name: 'Upload',
      path: '/upload',
      icon: Upload,
      adminOnly: false
    },
    {
      name: 'Manage Users',
      path: '/users',
      icon: Settings,
      adminOnly: true
    }
  ];

  const filteredNavItems = navItems.filter(item => !item.adminOnly || isAdmin);

  return (
    <div className="min-h-screen bg-[#030712]">
      {/* Sidebar */}
      <aside className={`fixed top-0 left-0 z-40 h-screen transition-transform duration-300 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      } w-72`}>
        {/* Sidebar background with gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-gray-900 via-gray-900 to-indigo-950/50"></div>
        <div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg width=\"30\" height=\"30\" viewBox=\"0 0 30 30\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Cpath d=\"M0 0h30v30H0z\" fill=\"none\"/%3E%3Cpath d=\"M15 0v30M0 15h30\" stroke=\"rgba(99,102,241,0.03)\" stroke-width=\"1\"/%3E%3C/svg%3E')]"></div>

        <div className="relative h-full flex flex-col border-r border-white/5">
          {/* Logo */}
          <div className="flex items-center justify-between p-5 border-b border-white/5">
            <div className="flex items-center gap-3">
              <div className="relative group">
                <div className="absolute inset-0 bg-cyan-500/20 blur-xl rounded-full scale-150 group-hover:bg-cyan-400/30 transition-all"></div>
                <img
                  src="/logo.png"
                  alt="Heimdall"
                  className="relative w-12 h-12 object-contain drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]"
                />
              </div>
              <div>
                <span className="text-xl font-bold bg-gradient-to-r from-white to-cyan-200 bg-clip-text text-transparent">HEIMDALL</span>
                <p className="text-xs text-gray-500">Security Platform</p>
              </div>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* User Info */}
          <div className="p-4 border-b border-white/5">
            <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-white/5 to-transparent rounded-xl border border-white/5 hover:border-cyan-500/20 transition-all cursor-pointer group">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate">
                  {user.username || 'User'}
                </p>
                <p className="text-xs text-gray-500">
                  {isAdmin ? 'Administrator' : 'Standard User'}
                </p>
              </div>
              <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-cyan-400 transition-colors" />
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto scrollbar-thin">
            <p className="px-3 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wider">
              Main Menu
            </p>
            {filteredNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`group flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-cyan-500/20 to-indigo-500/10 text-white border-l-2 border-cyan-400'
                      : 'text-gray-400 hover:bg-white/5 hover:text-white'
                  }`}
                >
                  <div className={`p-2 rounded-lg transition-all ${
                    isActive
                      ? 'bg-gradient-to-br from-cyan-500/30 to-indigo-500/30 shadow-lg shadow-cyan-500/10'
                      : 'bg-white/5 group-hover:bg-white/10'
                  }`}>
                    <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : ''}`} />
                  </div>
                  <span className="font-medium text-sm">{item.name}</span>
                  {isActive && (
                    <div className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-lg shadow-cyan-400/50"></div>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* System Status */}
          <div className="p-4 border-t border-white/5">
            <div className="p-3 rounded-xl bg-gradient-to-r from-emerald-500/10 to-transparent border border-emerald-500/20">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-lg shadow-emerald-400/50"></div>
                <span className="text-xs font-medium text-emerald-400">System Online</span>
              </div>
              <p className="text-xs text-gray-500">All services operational</p>
            </div>
          </div>

          {/* Logout Button */}
          <div className="p-4 border-t border-white/5">
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 px-3 py-2.5 w-full rounded-xl text-gray-400 hover:bg-red-500/10 hover:text-red-400 transition-all duration-200 group"
            >
              <div className="p-2 rounded-lg bg-white/5 group-hover:bg-red-500/20 transition-all">
                <LogOut className="w-4 h-4" />
              </div>
              <span className="font-medium text-sm">Sign Out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className={`transition-all duration-300 ${sidebarOpen ? 'lg:pl-72' : ''}`}>
        {/* Top Bar */}
        <header className="sticky top-0 z-30 bg-gray-900/80 backdrop-blur-xl border-b border-white/5">
          <div className="flex items-center justify-between px-6 py-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 transition-colors border border-white/5"
            >
              <Menu className="w-5 h-5 text-gray-400" />
            </button>

            <div className="flex items-center gap-4">
              <div className="hidden md:flex items-center gap-2 px-4 py-2 bg-white/5 rounded-xl border border-white/5">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span className="text-sm font-medium text-gray-400">
                  {new Date().toLocaleDateString('en-US', {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric'
                  })}
                </span>
              </div>
              <button className="relative p-2.5 rounded-xl bg-white/5 hover:bg-white/10 transition-colors border border-white/5">
                <Bell className="w-5 h-5 text-gray-400" />
                <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500 shadow-lg shadow-red-500/50"></span>
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="min-h-[calc(100vh-73px)] bg-gradient-to-br from-[#030712] via-gray-900 to-indigo-950/30">
          <Outlet />
        </main>
      </div>

      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}
