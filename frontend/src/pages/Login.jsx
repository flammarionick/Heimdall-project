// src/pages/Login.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Eye, EyeOff, Lock, User, AlertCircle } from 'lucide-react';

const BACKEND_BASE_URL = "http://127.0.0.1:5000";

export default function Login() {
  const navigate = useNavigate();
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`${BACKEND_BASE_URL}/auth/api/login`, {
        method: 'POST',
        credentials: 'include',       // IMPORTANT: allow cookies/session
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: credentials.username,
          password: credentials.password
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        setError(data.error || "Invalid credentials");
        setIsLoading(false);
        return;
      }

      // Successful login → redirect
      if (data.user?.is_admin) {
        navigate('/admin/dashboard');
      } else {
        navigate('/dashboard');
      }

    } catch (err) {
      console.error("Login error:", err);
      setError("Could not connect to server.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center p-4 relative overflow-hidden">

      {/* Login Card */}
      <div className="relative w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-2xl shadow-2xl mb-4">
            <Shield className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-2 tracking-tight">Heimdall</h1>
          <p className="text-blue-200 text-sm">Secure Inmate Recognition System</p>
        </div>

        <div className="bg-white/10 backdrop-blur-xl rounded-3xl shadow-2xl p-8 border border-white/20">
          <div className="space-y-6">

            {error && (
              <div className="p-4 bg-red-500/20 border border-red-400/50 rounded-xl flex items-start">
                <AlertCircle className="w-5 h-5 text-red-300 mr-2" />
                <p className="text-sm text-red-100">{error}</p>
              </div>
            )}

            {/* Username */}
            <div>
              <label className="text-sm font-semibold text-white/90">Username</label>
              <div className="relative">
                <User className="absolute inset-y-0 left-3 my-auto text-blue-300 w-5 h-5" />
                <input
                  type="text"
                  value={credentials.username}
                  onChange={e => setCredentials({ ...credentials, username: e.target.value })}
                  className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:ring-blue-400"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="text-sm font-semibold text-white/90">Password</label>
              <div className="relative">
                <Lock className="absolute inset-y-0 left-3 my-auto text-blue-300 w-5 h-5" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={credentials.password}
                  onChange={e => setCredentials({ ...credentials, password: e.target.value })}
                  className="w-full pl-10 pr-12 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:ring-blue-400"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-3 text-blue-300"
                >
                  {showPassword ? <EyeOff /> : <Eye />}
                </button>
              </div>
            </div>

            <button
              onClick={handleSubmit}
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 py-3 rounded-xl text-white font-semibold"
            >
              {isLoading ? "Authenticating..." : "Sign In"}
            </button>

          </div>
        </div>
      </div>
    </div>
  );
}