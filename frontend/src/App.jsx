// src/App.jsx
import { Routes, Route, Navigate } from "react-router-dom";

import Login from "./pages/Login";
import AdminDashboard from "./pages/AdminDashboard";
import UserDashboard from "./pages/UserDashboard";
import AlertsLogs from "./pages/AlertsLogs";
import Analytics from "./pages/Analytics";
import InmateProfiles from "./pages/InmateProfiles";
import LiveMonitoring from "./pages/LiveMonitoring";
import ManageCameras from "./pages/ManageCameras";
import ManageUsers from "./pages/ManageUsers";
import UploadRecognition from "./pages/UploadRecognition";

export default function App() {
  return (
    <Routes>
      {/* Auth */}
      <Route path="/login" element={<Login />} />

      {/* Admin views */}
      <Route path="/admin" element={<AdminDashboard />} />
      <Route path="/admin/dashboard" element={<AdminDashboard />} />
      <Route path="/admin/alerts" element={<AlertsLogs />} />
      <Route path="/admin/analytics" element={<Analytics />} />
      <Route path="/admin/inmates" element={<InmateProfiles />} />
      <Route path="/admin/live" element={<LiveMonitoring />} />
      <Route path="/admin/cameras" element={<ManageCameras />} />
      <Route path="/admin/users" element={<ManageUsers />} />
      <Route path="/admin/upload" element={<UploadRecognition />} />

      {/* Non-admin dashboard */}
      <Route path="/dashboard" element={<UserDashboard />} />

      {/* Default / catch-all */}
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}