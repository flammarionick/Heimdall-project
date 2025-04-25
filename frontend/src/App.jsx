import { useEffect, useState } from 'react';
import io from 'socket.io-client';

const socket = io('http://localhost:5000');

function App() {
  const [alerts, setAlerts] = useState([]);
  const [cameras, setCameras] = useState([]);

  useEffect(() => {
    socket.on('new_alert', (alert) => {
      setAlerts(prev => [alert, ...prev]);
      // Optionally, play an alarm sound here
    });

    socket.on('camera_status', (camera) => {
      setCameras(prev => {
        const updated = prev.filter(c => c.id !== camera.id);
        return [camera, ...updated];
      });
    });

    return () => {
      socket.off('new_alert');
      socket.off('camera_status');
    };
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <h1 className="text-3xl font-bold mb-6">Heimdall Dashboard</h1>

      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-4">Alerts</h2>
        <div className="space-y-4">
          {alerts.map((alert, index) => (
            <div key={index} className="p-4 bg-white rounded shadow">
              <p><strong>Message:</strong> {alert.message}</p>
              <p><strong>Level:</strong> {alert.level}</p>
              <p><strong>Timestamp:</strong> {new Date(alert.timestamp).toLocaleString()}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-4">Cameras</h2>
        <div className="space-y-4">
          {cameras.map((camera, index) => (
            <div key={index} className="p-4 bg-white rounded shadow">
              <p><strong>ID:</strong> {camera.id}</p>
              <p><strong>Status:</strong> {camera.active ? 'Active' : 'Inactive'}</p>
              <p><strong>Location:</strong> {camera.location}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default App;
