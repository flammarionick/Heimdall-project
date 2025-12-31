// frontend/src/components/EscapedInmateAlarm.jsx
/**
 * Full-screen alarm component for escaped inmate detection.
 * Plays siren audio on loop until manually dismissed.
 */

import { useEffect, useRef } from 'react';
import { AlertTriangle, X, MapPin, Clock, User, Shield } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || '';

function EscapedInmateAlarm({ inmate, alertId, detectionLocation, timestamp, onDismiss }) {
  const audioRef = useRef(null);

  useEffect(() => {
    // Play siren on loop
    try {
      audioRef.current = new Audio(`${API_BASE}/static/sounds/siren.wav`);
      audioRef.current.loop = true;
      audioRef.current.volume = 0.7;
      audioRef.current.play().catch(err => {
        console.warn('Audio autoplay blocked:', err);
      });
    } catch (err) {
      console.error('Failed to load siren audio:', err);
    }

    // Cleanup: stop audio when component unmounts
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
    };
  }, []);

  const handleDismiss = () => {
    // Stop audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    onDismiss();
  };

  const formatTime = (isoString) => {
    if (!isoString) return 'Unknown time';
    try {
      return new Date(isoString).toLocaleTimeString();
    } catch {
      return 'Unknown time';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-red-900/95 animate-pulse">
      {/* Background pulse effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-red-800 via-red-600 to-red-800 animate-gradient-x opacity-50" />

      {/* Main content */}
      <div className="relative z-10 bg-white rounded-2xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden">
        {/* Header */}
        <div className="bg-red-600 text-white px-6 py-4 flex items-center gap-3">
          <AlertTriangle className="w-8 h-8 animate-bounce" />
          <h1 className="text-2xl font-bold">ESCAPED INMATE DETECTED</h1>
        </div>

        {/* Inmate details */}
        <div className="p-6 space-y-4">
          {/* Mugshot and name */}
          <div className="flex items-center gap-4">
            {inmate.mugshot_path ? (
              <img
                src={`${API_BASE}${inmate.mugshot_path}`}
                alt={inmate.name}
                className="w-24 h-24 rounded-full object-cover border-4 border-red-500"
              />
            ) : (
              <div className="w-24 h-24 rounded-full bg-gray-200 flex items-center justify-center border-4 border-red-500">
                <User className="w-12 h-12 text-gray-400" />
              </div>
            )}
            <div>
              <h2 className="text-2xl font-bold text-gray-900">{inmate.name || 'Unknown'}</h2>
              <p className="text-gray-600">ID: {inmate.inmate_id}</p>
              {inmate.confidence && (
                <p className="text-red-600 font-semibold">{inmate.confidence}% match confidence</p>
              )}
            </div>
          </div>

          {/* Additional details */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            {inmate.risk_level && (
              <div className="flex items-center gap-2 bg-red-50 p-2 rounded">
                <Shield className="w-4 h-4 text-red-600" />
                <span className="font-medium">Risk: {inmate.risk_level}</span>
              </div>
            )}
            {inmate.crime && (
              <div className="flex items-center gap-2 bg-red-50 p-2 rounded col-span-2">
                <AlertTriangle className="w-4 h-4 text-red-600" />
                <span className="font-medium">Crime: {inmate.crime}</span>
              </div>
            )}
            {timestamp && (
              <div className="flex items-center gap-2 bg-gray-50 p-2 rounded">
                <Clock className="w-4 h-4 text-gray-600" />
                <span>{formatTime(timestamp)}</span>
              </div>
            )}
            {detectionLocation && detectionLocation.lat && (
              <div className="flex items-center gap-2 bg-gray-50 p-2 rounded">
                <MapPin className="w-4 h-4 text-gray-600" />
                <span>Location detected</span>
              </div>
            )}
          </div>

          {/* Warning message */}
          <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-3 text-yellow-800 text-sm">
            <strong>ALERT:</strong> This individual is classified as an escaped inmate.
            Exercise extreme caution and follow security protocols.
          </div>
        </div>

        {/* Dismiss button */}
        <div className="px-6 pb-6">
          <button
            onClick={handleDismiss}
            className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-4 px-6 rounded-lg
                     flex items-center justify-center gap-2 transition-colors text-lg"
          >
            <X className="w-5 h-5" />
            ACKNOWLEDGE ALERT
          </button>
          <p className="text-center text-gray-500 text-xs mt-2">
            Click to acknowledge and stop the alarm
          </p>
        </div>
      </div>
    </div>
  );
}

export default EscapedInmateAlarm;
