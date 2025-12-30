import { Routes, Route, Navigate } from "react-router-dom";
import { RequireAdmin, RequireUser } from "./routes/guards";

import Login from "./pages/Login.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";
import UserDashboard from "./pages/UserDashboard.jsx";
import AlertsLogs from "./pages/AlertsLogs.jsx";
import Analytics from "./pages/Analytics.jsx";
import InmateProfiles from "./pages/InmateProfiles.jsx";
import LiveMonitoring from "./pages/LiveMonitoring.jsx";
import ManageCameras from "./pages/ManageCameras.jsx";
import ManageUsers from "./pages/ManageUsers.jsx";
import UploadRecognition from "./pages/UploadRecognition.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Admin */}
      <Route
        path="/admin"
        element={
          <RequireAdmin>
            <AdminDashboard />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/dashboard"
        element={
          <RequireAdmin>
            <AdminDashboard />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/alerts"
        element={
          <RequireUser>
            <AlertsLogs />
          </RequireUser>
        }
      />
      <Route
        path="/admin/analytics"
        element={
          <RequireUser>
            <Analytics />
          </RequireUser>
        }
      />
      <Route
        path="/admin/inmates"
        element={
          <RequireUser>
            <InmateProfiles />
          </RequireUser>
        }
      />
      <Route
        path="/admin/live"
        element={
          <RequireUser>
            <LiveMonitoring />
          </RequireUser>
        }
      />
      <Route
        path="/admin/cameras"
        element={
          <RequireUser>
            <ManageCameras />
          </RequireUser>
        }
      />
      <Route
        path="/admin/users"
        element={
          <RequireAdmin>
            <ManageUsers />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/upload"
        element={
          <RequireUser>
            <UploadRecognition />
          </RequireUser>
        }
      />

      {/* User */}
      <Route
        path="/dashboard"
        element={
          <RequireUser>
            <UserDashboard />
          </RequireUser>
        }
      />

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}