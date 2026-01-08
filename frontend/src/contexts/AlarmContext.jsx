// src/contexts/AlarmContext.jsx
/**
 * Global Alarm Context for persistent alarm audio management.
 * - Audio continues playing even after dismissing the visual modal
 * - Plays in cycles: 10 minutes on, 5 minutes off
 * - Only stops when alert is resolved in the backend
 */

import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || '';

// Timing constants (in milliseconds)
const SOUND_ON_DURATION = 10 * 60 * 1000;  // 10 minutes
const SOUND_OFF_DURATION = 5 * 60 * 1000;  // 5 minutes
const RESOLVE_CHECK_INTERVAL = 10 * 1000;  // Check every 10 seconds

const AlarmContext = createContext(null);

export function AlarmProvider({ children }) {
  // Active alarms: Map of alertId -> alarm data
  const [activeAlarms, setActiveAlarms] = useState(new Map());
  // Visual modal state: which alarm to show (null = hidden)
  const [visibleAlarm, setVisibleAlarm] = useState(null);
  // Audio state
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [isInSilentPeriod, setIsInSilentPeriod] = useState(false);

  const audioRef = useRef(null);
  const cycleTimerRef = useRef(null);
  const resolveCheckRef = useRef(null);

  // Start playing the siren audio
  const startAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
    }

    try {
      audioRef.current = new Audio(`${API_BASE}/static/sounds/siren.wav`);
      audioRef.current.loop = true;
      audioRef.current.volume = 0.7;
      audioRef.current.play().catch(err => {
        console.warn('Audio autoplay blocked:', err);
      });
      setIsAudioPlaying(true);
      setIsInSilentPeriod(false);
    } catch (err) {
      console.error('Failed to load siren audio:', err);
    }
  }, []);

  // Stop/pause the audio
  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsAudioPlaying(false);
  }, []);

  // Start the 10min on / 5min off cycle
  const startSoundCycle = useCallback(() => {
    // Clear any existing timer
    if (cycleTimerRef.current) {
      clearTimeout(cycleTimerRef.current);
    }

    // Start playing
    startAudio();

    // After 10 minutes, pause for 5 minutes
    cycleTimerRef.current = setTimeout(() => {
      stopAudio();
      setIsInSilentPeriod(true);

      // After 5 minutes silence, restart cycle
      cycleTimerRef.current = setTimeout(() => {
        // Only restart if there are still active alarms
        if (activeAlarms.size > 0) {
          startSoundCycle();
        }
      }, SOUND_OFF_DURATION);
    }, SOUND_ON_DURATION);
  }, [startAudio, stopAudio, activeAlarms.size]);

  // Stop the sound cycle completely
  const stopSoundCycle = useCallback(() => {
    if (cycleTimerRef.current) {
      clearTimeout(cycleTimerRef.current);
      cycleTimerRef.current = null;
    }
    stopAudio();
    setIsInSilentPeriod(false);
  }, [stopAudio]);

  // Check if alarms are resolved in the backend
  const checkResolvedAlarms = useCallback(async () => {
    if (activeAlarms.size === 0) return;

    try {
      const res = await fetch(`${API_BASE}/api/alerts/`, {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });

      if (res.ok) {
        const data = await res.json();
        const alerts = data.alerts || data || [];

        // Check each active alarm
        const resolvedIds = [];
        activeAlarms.forEach((alarm, alertId) => {
          const backendAlert = alerts.find(a => a.id === alertId);
          if (backendAlert && (backendAlert.status === 'resolved' || backendAlert.resolved)) {
            resolvedIds.push(alertId);
          }
        });

        // Remove resolved alarms
        if (resolvedIds.length > 0) {
          setActiveAlarms(prev => {
            const next = new Map(prev);
            resolvedIds.forEach(id => next.delete(id));
            return next;
          });
        }
      }
    } catch (err) {
      console.error('Error checking resolved alarms:', err);
    }
  }, [activeAlarms]);

  // Trigger a new alarm
  const triggerAlarm = useCallback((alarmData) => {
    const alertId = alarmData.alert_id || alarmData.alertId || Date.now();

    setActiveAlarms(prev => {
      const next = new Map(prev);
      next.set(alertId, {
        ...alarmData,
        alertId,
        triggeredAt: new Date().toISOString()
      });
      return next;
    });

    // Show the visual modal
    setVisibleAlarm({
      ...alarmData,
      alertId
    });

    // Start sound cycle if not already running
    if (!isAudioPlaying && !isInSilentPeriod) {
      startSoundCycle();
    }
  }, [isAudioPlaying, isInSilentPeriod, startSoundCycle]);

  // Dismiss the visual modal (audio continues)
  const dismissVisual = useCallback(() => {
    setVisibleAlarm(null);
  }, []);

  // Manually stop alarm for a specific alert (when resolved via UI)
  const resolveAlarm = useCallback((alertId) => {
    setActiveAlarms(prev => {
      const next = new Map(prev);
      next.delete(alertId);
      return next;
    });

    // If this was the visible alarm, hide it
    if (visibleAlarm && visibleAlarm.alertId === alertId) {
      setVisibleAlarm(null);
    }
  }, [visibleAlarm]);

  // Stop all alarms (emergency stop)
  const stopAllAlarms = useCallback(() => {
    setActiveAlarms(new Map());
    setVisibleAlarm(null);
    stopSoundCycle();
  }, [stopSoundCycle]);

  // Start/stop sound cycle based on active alarms
  useEffect(() => {
    if (activeAlarms.size > 0) {
      // Start sound cycle if not running
      if (!isAudioPlaying && !isInSilentPeriod) {
        startSoundCycle();
      }

      // Start checking for resolved alarms
      if (!resolveCheckRef.current) {
        resolveCheckRef.current = setInterval(checkResolvedAlarms, RESOLVE_CHECK_INTERVAL);
      }
    } else {
      // No active alarms - stop everything
      stopSoundCycle();
      if (resolveCheckRef.current) {
        clearInterval(resolveCheckRef.current);
        resolveCheckRef.current = null;
      }
    }
  }, [activeAlarms.size, isAudioPlaying, isInSilentPeriod, startSoundCycle, stopSoundCycle, checkResolvedAlarms]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      if (cycleTimerRef.current) {
        clearTimeout(cycleTimerRef.current);
      }
      if (resolveCheckRef.current) {
        clearInterval(resolveCheckRef.current);
      }
    };
  }, []);

  const value = {
    // State
    activeAlarms,
    visibleAlarm,
    isAudioPlaying,
    isInSilentPeriod,
    hasActiveAlarms: activeAlarms.size > 0,

    // Actions
    triggerAlarm,
    dismissVisual,
    resolveAlarm,
    stopAllAlarms,
  };

  return (
    <AlarmContext.Provider value={value}>
      {children}
    </AlarmContext.Provider>
  );
}

export function useAlarm() {
  const context = useContext(AlarmContext);
  if (!context) {
    throw new Error('useAlarm must be used within an AlarmProvider');
  }
  return context;
}

export default AlarmContext;
