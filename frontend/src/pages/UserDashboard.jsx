import { useState, useEffect } from 'react';
import { Activity, Eye, Bell, Camera, TrendingUp, Clock, Shield, CheckCircle2 } from 'lucide-react';

export default function UserDashboard() {
  const [stats, setStats] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);

  useEffect(() => {
    // Mock data - replace with actual API calls
    setStats({
      todayMatches: 23,
      activeAlerts: 5,
      activeCameras: 12,
      systemStatus: 'operational'
    });

    setRecentActivity([
      { id: 1, type: 'match', message: 'Match detected at Main Entrance', time: '2 mins ago', level: 'warning' },
      { id: 2, type: 'camera', message: 'Camera B-101 came online', time: '15 mins ago', level: 'info' },
      { id: 3, type: 'alert', message: 'Alert resolved: Checkpoint Alpha', time: '1 hour ago', level: 'success' },
      { id: 4, type: 'match', message: 'Match detected at East Wing', time: '2 hours ago', level: 'warning' },
    ]);
  }, []);

  const StatCard = ({ icon: Icon, title, value, trend, color, bgColor }) => (
    <div className="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all transform hover:scale-[1.02] border border-gray-100">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-xl ${bgColor}`}>
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
        {trend && (
          <div className="flex items-center text-sm">
            <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
            <span className="text-green-600 font-semibold">{trend}</span>
          </div>
        )}
      </div>
      <h3 className="text-gray-500 text-sm font-medium mb-1">{title}</h3>
      <p className="text-3xl font-bold text-gray-800">{value}</p>
    </div>
  );

  const ActivityItem = ({ activity }) => {
    const getIcon = () => {
      switch (activity.type) {
        case 'match': return <Eye className="w-5 h-5" />;
        case 'camera': return <Camera className="w-5 h-5" />;
        case 'alert': return <Bell className="w-5 h-5" />;
        default: return <Activity className="w-5 h-5" />;
      }
    };

    const getColor = () => {
      switch (activity.level) {
        case 'warning': return 'bg-orange-100 text-orange-600 border-orange-200';
        case 'success': return 'bg-green-100 text-green-600 border-green-200';
        default: return 'bg-blue-100 text-blue-600 border-blue-200';
      }
    };

    return (
      <div className="flex items-start space-x-4 p-4 bg-white rounded-xl hover:bg-gray-50 transition-all border border-gray-100">
        <div className={`p-2 rounded-lg ${getColor()} border`}>
          {getIcon()}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800">{activity.message}</p>
          <p className="text-xs text-gray-500 mt-1 flex items-center">
            <Clock className="w-3 h-3 mr-1" />
            {activity.time}
          </p>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-gray-800 mb-2">Welcome Back</h1>
              <p className="text-gray-600 flex items-center">
                <Activity className="w-4 h-4 mr-2" />
                Your security monitoring dashboard
              </p>
            </div>
            <div className="bg-white px-4 py-2 rounded-xl shadow-md flex items-center">
              <Clock className="w-4 h-4 text-blue-500 mr-2" />
              <span className="text-sm font-medium text-gray-700">
                {new Date().toLocaleDateString('en-US', { 
                  weekday: 'long', 
                  month: 'long', 
                  day: 'numeric' 
                })}
              </span>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            icon={Eye}
            title="Today's Matches"
            value={stats?.todayMatches || 0}
            trend="+12%"
            color="text-blue-600"
            bgColor="bg-blue-100"
          />
          <StatCard
            icon={Bell}
            title="Active Alerts"
            value={stats?.activeAlerts || 0}
            color="text-orange-600"
            bgColor="bg-orange-100"
          />
          <StatCard
            icon={Camera}
            title="Active Cameras"
            value={stats?.activeCameras || 0}
            trend="+2"
            color="text-purple-600"
            bgColor="bg-purple-100"
          />
          <StatCard
            icon={Shield}
            title="System Status"
            value={stats?.systemStatus === 'operational' ? 'Operational' : 'Issues'}
            color="text-green-600"
            bgColor="bg-green-100"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Activity */}
          <div className="lg:col-span-2 bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-800">Recent Activity</h2>
              <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                View All
              </button>
            </div>
            <div className="space-y-3">
              {recentActivity.map(activity => (
                <ActivityItem key={activity.id} activity={activity} />
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="space-y-6">
            {/* System Health */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
              <h3 className="text-lg font-bold text-gray-800 mb-4">System Health</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600 flex items-center">
                      <CheckCircle2 className="w-4 h-4 mr-1 text-green-500" />
                      Camera Uptime
                    </span>
                    <span className="font-semibold text-gray-800">98.5%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full" style={{ width: '98.5%' }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600 flex items-center">
                      <CheckCircle2 className="w-4 h-4 mr-1 text-blue-500" />
                      Recognition Accuracy
                    </span>
                    <span className="font-semibold text-gray-800">94.2%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-gradient-to-r from-blue-500 to-cyan-500 h-2 rounded-full" style={{ width: '94.2%' }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600 flex items-center">
                      <CheckCircle2 className="w-4 h-4 mr-1 text-purple-500" />
                      Response Time
                    </span>
                    <span className="font-semibold text-gray-800">0.3s</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full" style={{ width: '85%' }}></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Access */}
            <div className="bg-gradient-to-br from-blue-500 to-cyan-500 rounded-2xl shadow-lg p-6 text-white">
              <h3 className="text-lg font-bold mb-4">Quick Access</h3>
              <div className="space-y-3">
                <button className="w-full bg-white/20 hover:bg-white/30 backdrop-blur-sm rounded-lg p-3 text-left transition-all border border-white/20">
                  <div className="flex items-center">
                    <Camera className="w-5 h-5 mr-3" />
                    <span className="font-medium">View Live Cameras</span>
                  </div>
                </button>
                <button className="w-full bg-white/20 hover:bg-white/30 backdrop-blur-sm rounded-lg p-3 text-left transition-all border border-white/20">
                  <div className="flex items-center">
                    <Bell className="w-5 h-5 mr-3" />
                    <span className="font-medium">Check Alerts</span>
                  </div>
                </button>
                <button className="w-full bg-white/20 hover:bg-white/30 backdrop-blur-sm rounded-lg p-3 text-left transition-all border border-white/20">
                  <div className="flex items-center">
                    <Eye className="w-5 h-5 mr-3" />
                    <span className="font-medium">Upload for Recognition</span>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}