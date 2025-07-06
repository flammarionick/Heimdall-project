import { useEffect, useState } from 'react';
import axios from 'axios';

export default function ManageUsers() {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = () => {
    axios.get('/api/users/')
      .then(res => setUsers(res.data))
      .catch(err => console.error('Failed to fetch users:', err));
  };

  const toggleStatus = (id) => {
    axios.patch(`/api/users/${id}/toggle`)
      .then(fetchUsers)
      .catch(err => console.error('Failed to toggle user:', err));
  };

  const deleteUser = (id) => {
    if (confirm('Are you sure you want to delete this user?')) {
      axios.delete(`/api/users/${id}`)
        .then(fetchUsers)
        .catch(err => console.error('Failed to delete user:', err));
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Manage Users</h1>
      <div className="overflow-x-auto bg-white shadow rounded-lg">
        <table className="min-w-full text-sm text-left">
          <thead className="bg-gray-100 border-b">
            <tr>
              <th className="p-3 font-semibold">Name</th>
              <th className="p-3 font-semibold">Email</th>
              <th className="p-3 font-semibold">Role</th>
              <th className="p-3 font-semibold">Status</th>
              <th className="p-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id} className="border-b hover:bg-gray-50">
                <td className="p-3">{user.name}</td>
                <td className="p-3">{user.email}</td>
                <td className="p-3">{user.is_admin ? 'Admin' : 'User'}</td>
                <td className="p-3">
                  <span className={`px-2 py-1 rounded-full text-white ${user.is_active ? 'bg-green-500' : 'bg-red-500'}`}>
                    {user.is_active ? 'Active' : 'Suspended'}
                  </span>
                </td>
                <td className="p-3 flex gap-2">
                  <button
                    onClick={() => toggleStatus(user.id)}
                    className="bg-yellow-500 hover:bg-yellow-600 text-white px-3 py-1 rounded"
                  >
                    Toggle
                  </button>
                  <button
                    onClick={() => deleteUser(user.id)}
                    className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

