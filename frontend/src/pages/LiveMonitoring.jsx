// src/pages/LiveMonitoring.jsx
import { useEffect, useState } from 'react';
import axios from 'axios';
import io from 'socket.io-client';

const socket = io('http://localhost:5000'); // Adjust backend URL as needed

export default function LiveMonitoring() {
  const [cameras, setCameras] = useState([]);
  const [formData, setFormData] = useState({ name: '', location: '' });

  useEffect(() => {
    axios.get('http://127.0.0.1:5000/api/cameras/')
      .then((res) => setCameras(res.data))
      .catch((err) => console.error('Error fetching cameras:', err));

    socket.on('camera_created', (camera) => {
      setCameras(prev => [...prev, camera]);
    });

    socket.on('camera_updated', (updatedCamera) => {
      setCameras(prev =>
        prev.map(cam => cam.id === updatedCamera.id ? updatedCamera : cam)
      );
    });

    socket.on('camera_deleted', ({ id }) => {
      setCameras(prev => prev.filter(cam => cam.id !== id));
    });

    return () => {
      socket.off('camera_created');
      socket.off('camera_updated');
      socket.off('camera_deleted');
    };
  }, []);

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const createCamera = async (e) => {
    e.preventDefault();
    if (!formData.name || !formData.location) {
      alert("Please fill in both name and location.");
      return;
    }

    try {
      await axios.post('http://127.0.0.1:5000/api/cameras/', formData);
      setFormData({ name: '', location: '' });
    } catch (err) {
      console.error('Create failed:', err);
    }
  };

  const toggleStatus = async (id) => {
    try {
      await axios.patch(`http://127.0.0.1:5000/api/cameras/${id}/toggle`);
    } catch (err) {
      console.error('Toggle failed:', err);
    }
  };

  const deleteCamera = async (id) => {
    if (!window.confirm('Are you sure you want to delete this camera?')) return;
    try {
      await axios.delete(`http://127.0.0.1:5000/api/cameras/${id}`);
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const editCamera = async (camera) => {
    const newName = prompt('New name:', camera.name);
    const newLocation = prompt('New location:', camera.location);
    if (!newName || !newLocation) return;

    try {
      await axios.put(`http://127.0.0.1:5000/api/cameras/${camera.id}`, {
        name: newName,
        location: newLocation
      });
    } catch (err) {
      console.error('Edit failed:', err);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-6">Live Monitoring</h1>

      <form onSubmit={createCamera} className="mb-8 bg-white p-4 rounded shadow-md grid grid-cols-1 md:grid-cols-3 gap-4">
        <input
          type="text"
          name="name"
          placeholder="Camera Name"
          value={formData.name}
          onChange={handleInputChange}
          className="border px-3 py-2 rounded"
          required
        />
        <input
          type="text"
          name="location"
          placeholder="Location"
          value={formData.location}
          onChange={handleInputChange}
          className="border px-3 py-2 rounded"
          required
        />
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition"
        >
          Add Camera
        </button>
      </form>

      {cameras.length === 0 ? (
        <p className="text-gray-500">No cameras found.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {cameras.map((camera) => (
            <div key={camera.id} className="bg-white shadow-md rounded-lg p-4">
              <h2 className="text-lg font-bold">{camera.name}</h2>
              <p className="text-sm text-gray-500 mb-2">{camera.location}</p>
              <div className="bg-black h-48 rounded mb-2 flex items-center justify-center text-white">
                Feed Not Available
              </div>
              <span
                className={`inline-block px-3 py-1 text-sm rounded-full ${
                  camera.status ? 'bg-green-500' : 'bg-red-500'
                } text-white`}
              >
                {camera.status ? 'Online' : 'Offline'}
              </span>
              <div className="flex gap-2 mt-3">
                <button
                  onClick={() => toggleStatus(camera.id)}
                  className="px-3 py-1 bg-yellow-500 text-white text-sm rounded"
                >
                  Toggle
                </button>
                <button
                  onClick={() => editCamera(camera)}
                  className="px-3 py-1 bg-blue-500 text-white text-sm rounded"
                >
                  Edit
                </button>
                <button
                  onClick={() => deleteCamera(camera.id)}
                  className="px-3 py-1 bg-red-600 text-white text-sm rounded"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

