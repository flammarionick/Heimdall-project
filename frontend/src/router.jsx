import { createBrowserRouter } from 'react-router-dom';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';
import UserDashboard from './pages/UserDashboard';
import LiveMonitoring from './pages/LiveMonitoring';
import InmateProfiles from './pages/InmateProfiles';
import ManageCameras from './pages/ManageCameras';
import AlertsLogs from './pages/AlertsLogs';
import Analytics from './pages/Analytics';
import UploadRecognition from './pages/UploadRecognition';
import ManageUsers from './pages/ManageUsers';

const router = createBrowserRouter([
  { path: '/', element: <Login /> },
  { path: '/admin', element: <AdminDashboard /> },
  { path: '/dashboard', element: <UserDashboard /> },
  { path: '/monitoring', element: <LiveMonitoring /> },
  { path: '/inmates', element: <InmateProfiles /> },
  { path: '/cameras', element: <ManageCameras /> },
  { path: '/alerts', element: <AlertsLogs /> },
  { path: '/analytics', element: <Analytics /> },
  { path: '/upload', element: <UploadRecognition /> },
  { path: '/users', element: <ManageUsers /> }
]);

export default router;
