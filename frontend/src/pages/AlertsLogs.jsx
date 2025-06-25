// src/pages/AlertsLogs.jsx
import { useEffect, useState } from 'react';
import axios from 'axios';
import io from 'socket.io-client';

const socket = io('http://localhost:5000');

export default function AlertsLogs() {
  const [alerts, setAlerts] = useState([]);

  // Load alerts and set up socket listeners
  useEffect(() => {
    axios.get('http://127.0.0.1:5000/api/alerts/')
      .then(res => setAlerts(res.data))
      .catch(err => console.error('Error fetching alerts:', err));

    socket.on('new_alert', (alert) => {
      setAlerts(prev => [alert, ...prev]);
    });

    return () => socket.off('new_alert');
  }, []);

  // Mark alert as resolved
  const handleResolve = async (alertId) => {
    try {
      await axios.post(`http://127.0.0.1:5000/api/alerts/${alertId}/resolve`);
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, resolved: true } : a));
    } catch (err) {
      console.error('Failed to resolve alert:', err);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Alerts & Logs</h1>
      {alerts.length === 0 ? (
        <p className="text-gray-500">No alerts found.</p>
      ) : (
        <div className="overflow-x-auto bg-white shadow rounded-lg">
          <table className="min-w-full text-sm text-left">
            <thead className="bg-gray-100 border-b">
              <tr>
                <th className="p-3 font-semibold">Time</th>
                <th className="p-3 font-semibold">Message</th>
                <th className="p-3 font-semibold">Inmate</th>
                <th className="p-3 font-semibold">Status</th>
                <th className="p-3 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map(alert => (
                <tr key={alert.id} className="border-b hover:bg-gray-50">
                  <td className="p-3">{new Date(alert.timestamp).toLocaleString()}</td>
                  <td className="p-3">{alert.message}</td>
                  <td className="p-3">
                    {alert.inmate_id
                      ? <a href={`/inmates/${alert.inmate_id}`} className="text-blue-600 underline">View Inmate</a>
                      : '—'}
                  </td>
                  <td className="p-3">
                    {alert.resolved ? (
                      <span className="text-green-600 font-semibold">Resolved</span>
                    ) : (
                      <span className="text-red-600 font-semibold">Unresolved</span>
                    )}
                  </td>
                  <td className="p-3">
                    {!alert.resolved && (
                      <button
                        onClick={() => handleResolve(alert.id)}
                        className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
                      >
                        Resolve
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
