// src/pages/UploadRecognition.jsx
import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const UploadRecognition = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [inmate, setInmate] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
    setInmate(null);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64Image = reader.result;
      setLoading(true);
      setError(null);

      try {
        const res = await axios.post('http://localhost:5000/recognition/api/predict', {
          image: base64Image,
        });

        if (res.data.inmate) {
          setInmate(res.data.inmate);
          // Auto-redirect after delay
          setTimeout(() => {
            navigate(`/inmates/${res.data.inmate.id}`, { state: { inmate: res.data.inmate } });
          }, 2000);
        } else {
          setError(res.data.error || 'No match found.');
        }
      } catch (err) {
        console.error(err);
        setError('Prediction failed. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    reader.readAsDataURL(selectedFile);
  };

  return (
    <div className="upload-page p-6 max-w-xl mx-auto">
      <h2 className="text-xl font-semibold mb-4">Upload Face Image for Recognition</h2>
      <form onSubmit={handleSubmit} className="space-y-4 bg-white p-4 rounded shadow">
        <input
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          required
          className="w-full border rounded px-3 py-2"
        />
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 w-full"
          disabled={loading}
        >
          {loading ? 'Processing...' : 'Submit'}
        </button>
      </form>

      {loading && <p className="text-blue-500 mt-4 animate-pulse">🔄 Checking identity...</p>}
      {error && <p className="text-red-600 mt-4">{error}</p>}

      {inmate && (
        <div className="mt-6 border p-4 rounded shadow bg-gray-50">
          <h3 className="text-lg font-bold mb-2">✅ Match Found</h3>
          <img
            src={inmate.image_url}
            alt={inmate.full_name}
            className="w-32 h-32 object-cover rounded mb-2"
          />
          <p><strong>Name:</strong> {inmate.full_name}</p>
          <p><strong>Age:</strong> {inmate.age}</p>
          <p><strong>Location:</strong> {inmate.location}</p>
        </div>
      )}
    </div>
  );
};

export default UploadRecognition;
