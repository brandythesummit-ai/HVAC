import { useState, useEffect, useRef } from 'react';
import { healthApi } from '../api/health';

/**
 * Health monitor hook with smart polling.
 *
 * Features:
 * - Smart polling intervals (30s/10s/5s based on health status)
 * - Pauses polling when tab is inactive
 * - Tracks last checked timestamp
 * - Handles errors gracefully
 */
export const useHealthMonitor = () => {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);
  const intervalRef = useRef(null);
  const isActiveRef = useRef(true);

  // Determine poll interval based on health status
  const getPollInterval = (healthStatus) => {
    if (!healthStatus) return 30000; // Default: 30s

    switch (healthStatus.status) {
      case 'down':
        return 5000; // 5 seconds when system is down
      case 'degraded':
        return 10000; // 10 seconds when degraded
      case 'healthy':
      default:
        return 30000; // 30 seconds when healthy
    }
  };

  // Fetch health data
  const fetchHealth = async () => {
    // Don't fetch if tab is inactive
    if (!isActiveRef.current) {
      return;
    }

    try {
      setError(null);
      const data = await healthApi.getHealth();
      setHealth(data);
      setLastChecked(new Date());
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
      // On error, assume system is down
      setHealth({ status: 'down', components: {}, summary: {} });
    }
  };

  // Handle visibility change (tab active/inactive)
  useEffect(() => {
    const handleVisibilityChange = () => {
      isActiveRef.current = !document.hidden;

      // If tab became active, fetch immediately
      if (isActiveRef.current) {
        fetchHealth();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  // Smart polling effect
  useEffect(() => {
    // Initial fetch
    fetchHealth();

    // Set up polling interval
    const pollInterval = getPollInterval(health);

    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    intervalRef.current = setInterval(fetchHealth, pollInterval);

    // Cleanup on unmount or when health changes
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [health?.status]); // Re-create interval when status changes

  return {
    health,
    loading,
    error,
    lastChecked,
    refetch: fetchHealth,
  };
};
