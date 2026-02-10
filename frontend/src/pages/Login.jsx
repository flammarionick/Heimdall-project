// src/pages/Login.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { User, Lock, Eye, EyeOff, AlertTriangle, Scan, Shield, Fingerprint, Zap } from "lucide-react";

export default function Login() {
  const navigate = useNavigate();

  const [form, setForm] = useState({ username: "", password: "" });
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onChange = (e) => {
    setForm((p) => ({ ...p, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/auth/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          username: form.username,
          password: form.password,
        }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setError(data?.error || "Login failed.");
        return;
      }

      if (data?.is_admin) {
        navigate("/admin/dashboard", { replace: true });
      } else {
        navigate("/dashboard", { replace: true });
      }
    } catch (err) {
      console.error(err);
      setError("Could not reach server. Is Flask running on :5000?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-[#030712]">
      {/* Animated Background */}
      <div className="absolute inset-0">
        {/* Main gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-950 via-[#030712] to-cyan-950"></div>

        {/* Animated orbs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/20 rounded-full blur-[128px] animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/20 rounded-full blur-[128px] animate-pulse" style={{ animationDelay: '1s' }}></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-[150px] animate-pulse" style={{ animationDelay: '0.5s' }}></div>

        {/* Grid overlay */}
        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: `linear-gradient(rgba(99,102,241,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.3) 1px, transparent 1px)`,
          backgroundSize: '50px 50px'
        }}></div>

        {/* Scanning line animation */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute w-full h-[2px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent animate-scan"></div>
        </div>
      </div>

      {/* Floating particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-cyan-400/40 rounded-full animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${5 + Math.random() * 10}s`
            }}
          ></div>
        ))}
      </div>

      {/* Main Content */}
      <div className="relative z-10 min-h-screen flex">
        {/* Left Panel - Branding */}
        <div className="hidden lg:flex lg:w-1/2 flex-col justify-center items-center p-12">
          {/* Logo with glow effect */}
          <div className="relative mb-8 group">
            <div className="absolute inset-0 bg-cyan-500/30 blur-3xl rounded-full scale-150 group-hover:bg-cyan-400/40 transition-all duration-500"></div>
            <img
              src="/logo.png"
              alt="Heimdall"
              className="relative w-48 h-48 object-contain drop-shadow-[0_0_30px_rgba(34,211,238,0.5)] group-hover:drop-shadow-[0_0_50px_rgba(34,211,238,0.7)] transition-all duration-500 group-hover:scale-105"
            />
          </div>

          <h1 className="text-5xl font-bold text-white mb-4 tracking-tight">
            <span className="bg-gradient-to-r from-white via-cyan-200 to-indigo-200 bg-clip-text text-transparent">
              HEIMDALL
            </span>
          </h1>
          <p className="text-xl text-cyan-300/80 mb-12 font-light tracking-wide">
            Security Intelligence Platform
          </p>

          {/* Feature cards */}
          <div className="space-y-4 w-full max-w-md">
            <div className="group flex items-center gap-4 p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm hover:bg-white/10 hover:border-cyan-500/30 transition-all duration-300">
              <div className="p-3 rounded-xl bg-gradient-to-br from-cyan-500/20 to-cyan-600/20 border border-cyan-500/20 group-hover:border-cyan-400/40 transition-all">
                <Scan className="w-6 h-6 text-cyan-400" />
              </div>
              <div>
                <h3 className="text-white font-semibold">Real-Time Recognition</h3>
                <p className="text-sm text-gray-400">AI-powered facial analysis with 99%+ accuracy</p>
              </div>
            </div>

            <div className="group flex items-center gap-4 p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm hover:bg-white/10 hover:border-indigo-500/30 transition-all duration-300">
              <div className="p-3 rounded-xl bg-gradient-to-br from-indigo-500/20 to-indigo-600/20 border border-indigo-500/20 group-hover:border-indigo-400/40 transition-all">
                <Fingerprint className="w-6 h-6 text-indigo-400" />
              </div>
              <div>
                <h3 className="text-white font-semibold">Biometric Analysis</h3>
                <p className="text-sm text-gray-400">Multi-factor identification algorithms</p>
              </div>
            </div>

            <div className="group flex items-center gap-4 p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm hover:bg-white/10 hover:border-emerald-500/30 transition-all duration-300">
              <div className="p-3 rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/20 border border-emerald-500/20 group-hover:border-emerald-400/40 transition-all">
                <Zap className="w-6 h-6 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-white font-semibold">Instant Alerts</h3>
                <p className="text-sm text-gray-400">24/7 monitoring with real-time notifications</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - Login Form */}
        <div className="flex-1 flex items-center justify-center p-6 lg:p-12">
          <div className="w-full max-w-md">
            {/* Mobile Logo */}
            <div className="lg:hidden flex flex-col items-center mb-8">
              <img
                src="/logo.png"
                alt="Heimdall"
                className="w-24 h-24 object-contain drop-shadow-[0_0_20px_rgba(34,211,238,0.5)] mb-4"
              />
              <h1 className="text-3xl font-bold text-white">HEIMDALL</h1>
              <p className="text-cyan-400/80 text-sm">Security Intelligence Platform</p>
            </div>

            {/* Login Card */}
            <div className="relative">
              {/* Card glow effect */}
              <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500/20 via-indigo-500/20 to-cyan-500/20 rounded-3xl blur-xl"></div>

              <div className="relative bg-gray-900/80 backdrop-blur-xl rounded-3xl border border-white/10 overflow-hidden">
                {/* Card header gradient */}
                <div className="h-1 bg-gradient-to-r from-cyan-500 via-indigo-500 to-cyan-500"></div>

                <div className="p-8">
                  <div className="text-center mb-8">
                    <h2 className="text-2xl font-bold text-white mb-2">Welcome Back</h2>
                    <p className="text-gray-400">Enter your credentials to access the system</p>
                  </div>

                  {error && (
                    <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-red-300">{error}</p>
                    </div>
                  )}

                  <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Username
                      </label>
                      <div className="relative group">
                        <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/20 to-indigo-500/20 rounded-xl blur opacity-0 group-focus-within:opacity-100 transition-opacity"></div>
                        <div className="relative">
                          <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 group-focus-within:text-cyan-400 transition-colors" />
                          <input
                            name="username"
                            value={form.username}
                            onChange={onChange}
                            autoComplete="username"
                            className="w-full pl-12 pr-4 py-3.5 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:bg-gray-800 focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20 transition-all outline-none"
                            placeholder="Enter your username"
                            required
                          />
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Password
                      </label>
                      <div className="relative group">
                        <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/20 to-indigo-500/20 rounded-xl blur opacity-0 group-focus-within:opacity-100 transition-opacity"></div>
                        <div className="relative">
                          <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 group-focus-within:text-cyan-400 transition-colors" />
                          <input
                            name="password"
                            type={showPw ? "text" : "password"}
                            value={form.password}
                            onChange={onChange}
                            autoComplete="current-password"
                            className="w-full pl-12 pr-12 py-3.5 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:bg-gray-800 focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20 transition-all outline-none"
                            placeholder="Enter your password"
                            required
                          />
                          <button
                            type="button"
                            onClick={() => setShowPw((v) => !v)}
                            className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-cyan-400 transition-colors"
                          >
                            {showPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                          </button>
                        </div>
                      </div>
                    </div>

                    <button
                      disabled={loading}
                      className="relative w-full group"
                    >
                      <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-indigo-500 rounded-xl blur opacity-60 group-hover:opacity-100 transition-opacity"></div>
                      <div className="relative flex items-center justify-center gap-2 px-6 py-3.5 bg-gradient-to-r from-cyan-600 to-indigo-600 rounded-xl text-white font-semibold hover:from-cyan-500 hover:to-indigo-500 transition-all disabled:opacity-50">
                        {loading ? (
                          <>
                            <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                            <span>Authenticating...</span>
                          </>
                        ) : (
                          <>
                            <Shield className="w-5 h-5" />
                            <span>Secure Sign In</span>
                          </>
                        )}
                      </div>
                    </button>
                  </form>
                </div>

                {/* Card footer */}
                <div className="px-8 py-4 bg-gray-800/30 border-t border-white/5">
                  <p className="text-center text-gray-500 text-sm">
                    Protected by advanced encryption
                  </p>
                </div>
              </div>
            </div>

            {/* Footer text */}
            <p className="text-center text-gray-600 text-sm mt-8">
              Heimdall Security Intelligence System v2.0
            </p>
          </div>
        </div>
      </div>

      {/* Custom styles for animations */}
      <style>{`
        @keyframes scan {
          0% { top: -2px; opacity: 0; }
          50% { opacity: 1; }
          100% { top: 100%; opacity: 0; }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0) translateX(0); opacity: 0.4; }
          25% { transform: translateY(-20px) translateX(10px); opacity: 0.8; }
          50% { transform: translateY(-40px) translateX(-10px); opacity: 0.4; }
          75% { transform: translateY(-20px) translateX(5px); opacity: 0.8; }
        }
        .animate-scan {
          animation: scan 4s ease-in-out infinite;
        }
        .animate-float {
          animation: float 10s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
