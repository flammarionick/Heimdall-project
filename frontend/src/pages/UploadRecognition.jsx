// src/pages/UploadRecognition.jsx
import { useState } from 'react';
import axios from 'axios';

export default function UploadRecognition() {
  const [inmateName, setInmateName] = useState('');
  const [location, setLocation] = useState('');
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !inmateName || !location) {
      setStatus('Please fill all fields and choose an image.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('inmate_name', inmateName);
    formData.append('location', location);

    try {
      const response = await axios.post('http://127.0.0.1:5000/api/upload-recognition', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setStatus(`Success: ${response.data.message}`);
    } catch (err) {
      setStatus('Upload failed.');
      console.error(err);
    }
  };

  return (
    <div className="p-6 max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Upload Recognition Data</h1>
      <form onSubmit={handleSubmit} className="space-y-4 bg-white p-4 rounded shadow">
        <div>
          <label className="block font-medium mb-1">Inmate Name</label>
          <input
            type="text"
            value={inmateName}
            onChange={(e) => setInmateName(e.target.value)}
            className="w-full border px-3 py-2 rounded"
            required
          />
        </div>
        <div>
          <label className="block font-medium mb-1">Location / Camera Zone</label>
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="w-full border px-3 py-2 rounded"
            required
          />
        </div>
        <div>
          <label className="block font-medium mb-1">Face Image</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files[0])}
            className="w-full"
            required
          />
        </div>
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Upload
        </button>
        {status && <p className="text-sm mt-2">{status}</p>}
      </form>
    </div>
  );
}