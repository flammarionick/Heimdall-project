// src/components/AlarmIndicator.jsx
/**
 * Global alarm indicator shown on all pages when an alarm is active.
 * Provides quick access to resolve alarms without navigating away.
 */

import { Volume2, VolumeX, AlertTriangle } from 'lucide-react';
import { useAlarm } from '../contexts/AlarmContext';
import { Link } from 'react-router-dom';

function AlarmIndicator() {
  const { hasActiveAlarms, isAudioPlaying, isInSilentPeriod, activeAlarms } = useAlarm();

  if (!hasActiveAlarms) return null;

  const alarmCount = activeAlarms.size;

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div className="bg-red-600 text-white rounded-2xl shadow-2xl p-4 max-w-sm animate-pulse">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0">
            {isAudioPlaying ? (
              <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center">
                <Volume2 className="w-6 h-6 animate-pulse" />
              </div>
            ) : isInSilentPeriod ? (
              <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center">
                <VolumeX className="w-6 h-6 opacity-70" />
              </div>
            ) : (
              <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6" />
              </div>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <h4 className="font-bold text-lg">
              {alarmCount} Active Alarm{alarmCount !== 1 ? 's' : ''}
            </h4>
            <p className="text-red-100 text-sm truncate">
              {isAudioPlaying
                ? 'Alarm sounding'
                : isInSilentPeriod
                  ? 'Silent period - resumes soon'
                  : 'Alert requires attention'}
            </p>
          </div>
        </div>

        <div className="mt-3 flex gap-2">
          <Link
            to="/admin/alerts"
            className="flex-1 bg-white text-red-600 text-center py-2 px-4 rounded-xl font-semibold hover:bg-red-50 transition-colors text-sm"
          >
            View & Resolve
          </Link>
        </div>
      </div>
    </div>
  );
}

export default AlarmIndicator;
