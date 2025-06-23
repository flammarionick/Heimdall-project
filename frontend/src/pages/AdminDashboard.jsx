// pages/AdminDashboard.jsx
import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { Line, Pie } from 'react-chartjs-2';
import Chart from 'chart.js/auto';

const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const lineChartRef = useRef(null);
  const pieChartRef = useRef(null);

  useEffect(() => {
    axios.get('/api/admin/dashboard-stats')
      .then(res => setStats(res.data))
      .catch(err => console.error(err));
  }, []);

  // ✅ Cleanup on unmount
  useEffect(() => {
    return () => {
      if (lineChartRef.current) {
        lineChartRef.current.destroy();
      }
      if (pieChartRef.current) {
        pieChartRef.current.destroy();
      }
    };
  }, []);

  if (!stats) return <div>Loading...</div>;

  const lineChartData = {
    labels: stats.matches_over_time.map(item => item.date),
    datasets: [{
      label: 'Matches',
      data: stats.matches_over_time.map(item => item.count),
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59, 130, 246, 0.2)',
      fill: true,
    }]
  };

  const pieChartData = {
    labels: Object.keys(stats.inmate_status_counts),
    datasets: [{
      data: Object.values(stats.inmate_status_counts),
      backgroundColor: ['#22c55e', '#ef4444']
    }]
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Admin Dashboard</h1>
      <div className="grid grid-cols-3 gap-6 mb-8">
        <Card title="Total Users" value={stats.total_users} />
        <Card title="Active Users" value={stats.active_users} />
        <Card title="Suspended Users" value={stats.suspended_users} />
        <Card title="Total Cameras" value={stats.total_cameras} />
        <Card title="Total Alerts" value={stats.total_alerts} />
        <Card title="Total Inmates" value={stats.total_inmates} />
      </div>
      <div className="grid grid-cols-2 gap-8">
        <div className="bg-white shadow p-5 rounded-lg">
          <h2 className="font-semibold text-lg mb-2">Matches Over Time</h2>
          <Line
            ref={(el) => {
              if (lineChartRef.current && lineChartRef.current !== el) {
                lineChartRef.current.destroy();
              }
              lineChartRef.current = el;
            }}
            data={lineChartData}
          />
        </div>
        <div className="bg-white shadow p-5 rounded-lg">
          <h2 className="font-semibold text-lg mb-2">Inmate Status</h2>
          <Pie
            ref={(el) => {
              if (pieChartRef.current && pieChartRef.current !== el) {
                pieChartRef.current.destroy();
              }
              pieChartRef.current = el;
            }}
            data={pieChartData}
          />
        </div>
      </div>
    </div>
  );
};

const Card = ({ title, value }) => (
  <div className="bg-white shadow rounded-lg p-5">
    <h2 className="text-lg font-semibold mb-2">{title}</h2>
    <p className="text-3xl font-bold">{value}</p>
  </div>
);

export default AdminDashboard;
