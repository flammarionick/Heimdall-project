// src/App.jsx
import { Routes, Route, Navigate } from "react-router-dom";
import io from "socket.io-client";
import AdminDashboard from "./pages/AdminDashboard.jsx";

// If you *do* have a LoginPage later, replace DummyLogin with that.
function DummyLogin() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white rounded-xl shadow p-8">
        <h1 className="text-2xl font-bold mb-2">Heimdall Login</h1>
        <p className="text-gray-600 text-sm">
          This is a placeholder. Backend will POST to /auth/login and then
          redirect to /admin/dashboard.
        </p>
      </div>
    </div>
  );
}

const socket = io("http://localhost:5000", {
  withCredentials: true,
});

export default function App() {
  return (
    <Routes>
      {/* default route - placeholder login */}
      <Route path="/" element={<DummyLogin />} />

      {/* Flask redirects to this after login:
          return redirect(f"{FRONTEND_URL}/admin/dashboard")
      */}
      <Route
        path="/admin/dashboard"
        element={<AdminDashboard socket={socket} />}
      />

      {/* catch-all: if anything weird, push to /admin/dashboard */}
      <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
    </Routes>
  );
}