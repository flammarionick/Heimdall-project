// frontend/src/App.jsx
import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/Login.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";

function App() {
  return (
    <Routes>
      {/* Root sends you to backend login (via LoginPage redirect) */}
      <Route path="/" element={<LoginPage />} />

      {/* This is where Flask redirects after successful login */}
      <Route path="/admin/dashboard" element={<AdminDashboard />} />

      {/* Fallback: unknown routes go to login */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;