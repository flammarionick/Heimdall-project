// src/pages/UploadRecognition.jsx
import { useState } from 'react';
import { Upload, Camera, User, MapPin, Calendar, AlertTriangle, CheckCircle2, Loader2, FileImage } from 'lucide-react';

export default function UploadRecognition() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
      setResult(null);
      
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      const fakeEvent = { target: { files: [file] } };
      handleFileChange(fakeEvent);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleSubmit = () => {
    if (!selectedFile) return;
    
    setLoading(true);
    setError(null);
    
    setTimeout(() => {
      const matchFound = Math.random() > 0.3;
      
      if (matchFound) {
        setResult({
          match: true,
          inmate: {
            id: 'INM-2341',
            full_name: 'John Doe',
            age: 34,
            location: 'Kuje Correctional Facility',
            status: 'Escaped',
            lastSeen: 'July 5, 2022',
            crime: 'Armed Robbery',
            riskLevel: 'High',
            image_url: preview,
            confidence: '94.2%'
          }
        });
      } else {
        setError('No match found in the database');
      }
      
      setLoading(false);
    }, 2500);
  };

  const reset = () => {
    setSelectedFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">Face Recognition</h1>
          <p className="text-gray-600 flex items-center">
            <Camera className="w-4 h-4 mr-2" />
            Upload an image for facial recognition analysis
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
              <h2 className="text-xl font-bold text-gray-800 mb-4">Upload Image</h2>
              
              {!preview ? (
                <div
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  className="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center hover:border-blue-400 transition-all cursor-pointer bg-gray-50 hover:bg-blue-50"
                >
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileChange}
                    className="hidden"
                    id="file-upload"
                  />
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <div className="flex flex-col items-center">
                      <div className="p-4 bg-blue-100 rounded-full mb-4">
                        <Upload className="w-8 h-8 text-blue-600" />
                      </div>
                      <p className="text-lg font-semibold text-gray-700 mb-2">
                        Drop image here or click to upload
                      </p>
                      <p className="text-sm text-gray-500">
                        Supports JPG, PNG (Max 10MB)
                      </p>
                    </div>
                  </label>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="relative rounded-xl overflow-hidden border-2 border-gray-200">
                    <img
                      src={preview}
                      alt="Preview"
                      className="w-full h-96 object-cover"
                    />
                    <div className="absolute top-3 right-3">
                      <button
                        onClick={reset}
                        className="px-3 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-all"
                      >
                        Remove
                      </button>
                    </div>
                  </div>

                  <button
                    onClick={handleSubmit}
                    disabled={loading}
                    className="w-full py-4 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-bold rounded-xl shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center text-lg"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-6 h-6 mr-2 animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Camera className="w-6 h-6 mr-2" />
                        Analyze Face
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            <div className="bg-blue-50 rounded-2xl p-6 border border-blue-100">
              <h3 className="text-lg font-bold text-blue-900 mb-3 flex items-center">
                <FileImage className="w-5 h-5 mr-2" />
                Best Practices
              </h3>
              <ul className="space-y-2 text-sm text-blue-800">
                <li className="flex items-start">
                  <CheckCircle2 className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                  Use clear, well-lit frontal face images
                </li>
                <li className="flex items-start">
                  <CheckCircle2 className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                  Ensure face is visible without obstructions
                </li>
                <li className="flex items-start">
                  <CheckCircle2 className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                  Higher resolution images yield better results
                </li>
                <li className="flex items-start">
                  <CheckCircle2 className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                  Avoid blurry or heavily filtered images
                </li>
              </ul>
            </div>
          </div>

          <div>
            <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100 min-h-[500px]">
              <h2 className="text-xl font-bold text-gray-800 mb-6">Recognition Results</h2>

              {!loading && !result && !error && (
                <div className="flex flex-col items-center justify-center h-96 text-gray-400">
                  <Camera className="w-24 h-24 mb-4 opacity-30" />
                  <p className="text-lg">Upload an image to start analysis</p>
                </div>
              )}

              {loading && (
                <div className="flex flex-col items-center justify-center h-96">
                  <div className="relative">
                    <div className="w-24 h-24 border-8 border-blue-100 rounded-full"></div>
                    <div className="w-24 h-24 border-8 border-blue-500 border-t-transparent rounded-full animate-spin absolute top-0"></div>
                  </div>
                  <p className="text-lg font-semibold text-gray-700 mt-6">Analyzing facial features...</p>
                  <p className="text-sm text-gray-500 mt-2">This may take a few moments</p>
                </div>
              )}

              {error && (
                <div className="flex flex-col items-center justify-center h-96">
                  <div className="p-6 bg-red-100 rounded-full mb-4">
                    <AlertTriangle className="w-16 h-16 text-red-600" />
                  </div>
                  <p className="text-xl font-bold text-gray-800 mb-2">No Match Found</p>
                  <p className="text-gray-600 text-center">{error}</p>
                  <button
                    onClick={reset}
                    className="mt-6 px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-xl transition-all"
                  >
                    Try Another Image
                  </button>
                </div>
              )}

              {result && result.match && (
                <div className="space-y-6 animate-fadeIn">
                  <div className="bg-gradient-to-r from-red-500 to-orange-500 text-white rounded-xl p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <AlertTriangle className="w-6 h-6 mr-3" />
                        <div>
                          <p className="font-bold text-lg">Match Found</p>
                          <p className="text-sm text-white/90">High-risk individual detected</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold">{result.inmate.confidence}</p>
                        <p className="text-xs text-white/90">Confidence</p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center space-x-4 pb-4 border-b">
                      <div className="w-20 h-20 rounded-full overflow-hidden border-4 border-blue-500">
                        <img src={result.inmate.image_url} alt={result.inmate.full_name} className="w-full h-full object-cover" />
                      </div>
                      <div>
                        <h3 className="text-2xl font-bold text-gray-800">{result.inmate.full_name}</h3>
                        <p className="text-gray-600">{result.inmate.id}</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center text-gray-600 mb-1">
                          <User className="w-4 h-4 mr-2" />
                          <span className="text-sm font-medium">Age</span>
                        </div>
                        <p className="text-lg font-bold text-gray-800">{result.inmate.age} years</p>
                      </div>

                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center text-gray-600 mb-1">
                          <AlertTriangle className="w-4 h-4 mr-2" />
                          <span className="text-sm font-medium">Risk Level</span>
                        </div>
                        <span className="inline-block px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-bold">
                          {result.inmate.riskLevel}
                        </span>
                      </div>

                      <div className="bg-gray-50 rounded-lg p-4 col-span-2">
                        <div className="flex items-center text-gray-600 mb-1">
                          <MapPin className="w-4 h-4 mr-2" />
                          <span className="text-sm font-medium">Last Known Location</span>
                        </div>
                        <p className="text-lg font-bold text-gray-800">{result.inmate.location}</p>
                      </div>

                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center text-gray-600 mb-1">
                          <Calendar className="w-4 h-4 mr-2" />
                          <span className="text-sm font-medium">Last Seen</span>
                        </div>
                        <p className="text-sm font-bold text-gray-800">{result.inmate.lastSeen}</p>
                      </div>

                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center text-gray-600 mb-1">
                          <AlertTriangle className="w-4 h-4 mr-2" />
                          <span className="text-sm font-medium">Status</span>
                        </div>
                        <span className="inline-block px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm font-bold">
                          {result.inmate.status}
                        </span>
                      </div>

                      <div className="bg-red-50 rounded-lg p-4 col-span-2 border border-red-200">
                        <div className="flex items-center text-red-600 mb-1">
                          <AlertTriangle className="w-4 h-4 mr-2" />
                          <span className="text-sm font-medium">Crime</span>
                        </div>
                        <p className="text-lg font-bold text-red-800">{result.inmate.crime}</p>
                      </div>
                    </div>

                    <button className="w-full py-3 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-semibold rounded-xl transition-all shadow-lg">
                      View Full Profile
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn { animation: fadeIn 0.5s ease-out; }
      `}</style>
    </div>
  );
}