// src/pages/Login.jsx
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import axios from 'axios';

export default function Login() {
  const navigate = useNavigate();
  const [credentials, setCredentials] = useState({ username: '', password: '' });

  const handleSubmit = async (e) => {
    e.preventDefault();
    console.log("Submitting credentials:", credentials);

    try {
      const response = await axios.post(
        'http://127.0.0.1:5000/auth/api/login',
        {
          email: credentials.username,  // backend handles this as email or username
          password: credentials.password
        },
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      const { role } = response.data;
      if (role === 'admin') navigate('/admin');
      else navigate('/dashboard');
    } catch (err) {
      console.error("Login failed:", err.response?.data || err.message);
      alert('Login failed. Please check your credentials.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-tr from-gray-900 via-gray-800 to-black flex items-center justify-center px-4">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-xl shadow-2xl p-10 w-full max-w-md"
      >
        <h1 className="text-3xl font-extrabold text-center text-gray-800 mb-8">
          Heimdall Login
        </h1>
        <div className="mb-5">
          <label className="block text-sm font-semibold text-gray-700 mb-1">
            Username or Email
          </label>
          <input
            type="text"
            placeholder="admin or admin@email.com"
            className="w-full px-4 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={credentials.username}
            onChange={(e) =>
              setCredentials({ ...credentials, username: e.target.value })
            }
            required
          />
        </div>
        <div className="mb-6">
          <label className="block text-sm font-semibold text-gray-700 mb-1">
            Password
          </label>
          <input
            type="password"
            placeholder="Enter password"
            className="w-full px-4 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={credentials.password}
            onChange={(e) =>
              setCredentials({ ...credentials, password: e.target.value })
            }
            required
          />
        </div>
        <button
          type="submit"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-md font-semibold transition duration-150"
        >
          Login
        </button>
      </form>
    </div>
  );
}


