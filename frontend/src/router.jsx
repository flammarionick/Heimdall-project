import { createBrowserRouter, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import AdminDashboard from './pages/AdminDashboard';
import UserDashboard from './pages/UserDashboard';
import LiveMonitoring from './pages/LiveMonitoring';
import InmateProfiles from './pages/InmateProfiles';
import ManageCameras from './pages/ManageCameras';
import AlertsLogs from './pages/AlertsLogs';
import Analytics from './pages/Analytics';
import UploadRecognition from './pages/UploadRecognition';
import ManageUsers from './pages/ManageUsers';
import Layout from './components/Layout';

// Protected Route Component
function ProtectedRoute({ children, requireAdmin = false }) {
  const [isAuthenticated, setIsAuthenticated] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    // Check authentication with Flask backend
    fetch('/api/auth/check')
      .then(res => res.json())
      .then(data => {
        setIsAuthenticated(data.authenticated);
        setIsAdmin(data.user?.is_admin || false);
      })
      .catch(() => {
        setIsAuthenticated(false);
      });
  }, []);

  // Loading state
  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Not authenticated - redirect to login
  if (!isAuthenticated) {
    window.location.href = '/login';
    return null;
  }

  // Requires admin but user is not admin
  if (requireAdmin && !isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <ProtectedRoute><Layout /></ProtectedRoute>,
    children: [
      {
        path: '/admin',
        element: <ProtectedRoute requireAdmin={true}><AdminDashboard /></ProtectedRoute>
      },
      {
        path: '/dashboard',
        element: <ProtectedRoute><UserDashboard /></ProtectedRoute>
      },
      {
        path: '/monitoring',
        element: <ProtectedRoute><LiveMonitoring /></ProtectedRoute>
      },
      {
        path: '/inmates',
        element: <ProtectedRoute><InmateProfiles /></ProtectedRoute>
      },
      {
        path: '/cameras',
        element: <ProtectedRoute><ManageCameras /></ProtectedRoute>
      },
      {
        path: '/alerts',
        element: <ProtectedRoute><AlertsLogs /></ProtectedRoute>
      },
      {
        path: '/analytics',
        element: <ProtectedRoute><Analytics /></ProtectedRoute>
      },
      {
        path: '/upload',
        element: <ProtectedRoute><UploadRecognition /></ProtectedRoute>
      },
      {
        path: '/users',
        element: <ProtectedRoute requireAdmin={true}><ManageUsers /></ProtectedRoute>
      }
    ]
  }
]);

export default router;