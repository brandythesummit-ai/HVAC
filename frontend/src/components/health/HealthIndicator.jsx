import { useState } from 'react';
import { Activity, AlertCircle, AlertTriangle } from 'lucide-react';
import { useHealthMonitor } from '../../hooks/useHealthMonitor';
import HealthDetailModal from './HealthDetailModal';

/**
 * Health status indicator component.
 *
 * Displays a compact status indicator in the header that shows:
 * - Green pulsing dot + "All Systems Healthy" (healthy)
 * - Yellow dot + "System Degraded" (degraded)
 * - Red dot + "System Issues Detected" (down)
 * - Gray dot + "Checking..." (loading)
 *
 * Click to open detailed health modal.
 */
const HealthIndicator = () => {
  const { health, loading, lastChecked } = useHealthMonitor();
  const [modalOpen, setModalOpen] = useState(false);

  // Determine status display
  const getStatusDisplay = () => {
    if (loading && !health) {
      return {
        color: 'gray',
        bgColor: 'bg-gray-100',
        textColor: 'text-gray-600',
        dotColor: 'bg-gray-500',
        text: 'Checking...',
        animate: false,
      };
    }

    if (!health) {
      return {
        color: 'red',
        bgColor: 'bg-red-50',
        textColor: 'text-red-600',
        dotColor: 'bg-red-500',
        text: 'Unknown Status',
        animate: false,
      };
    }

    switch (health.status) {
      case 'healthy':
        return {
          color: 'green',
          bgColor: 'bg-green-50',
          textColor: 'text-green-700',
          dotColor: 'bg-green-500',
          text: 'All Systems Healthy',
          animate: true,
        };
      case 'degraded':
        return {
          color: 'yellow',
          bgColor: 'bg-yellow-50',
          textColor: 'text-yellow-700',
          dotColor: 'bg-yellow-500',
          text: 'System Degraded',
          animate: false,
        };
      case 'down':
        return {
          color: 'red',
          bgColor: 'bg-red-50',
          textColor: 'text-red-600',
          dotColor: 'bg-red-500',
          text: 'System Issues Detected',
          animate: false,
        };
      default:
        return {
          color: 'gray',
          bgColor: 'bg-gray-100',
          textColor: 'text-gray-600',
          dotColor: 'bg-gray-500',
          text: 'Unknown Status',
          animate: false,
        };
    }
  };

  const status = getStatusDisplay();

  return (
    <>
      <button
        onClick={() => setModalOpen(true)}
        className={`flex items-center px-3 py-1.5 text-sm ${status.textColor} ${status.bgColor} rounded-lg hover:opacity-80 transition-opacity cursor-pointer`}
        title="Click to view detailed health status"
      >
        <div
          className={`w-2 h-2 mr-2 ${status.dotColor} rounded-full ${
            status.animate ? 'animate-pulse' : ''
          }`}
        />
        <span>{status.text}</span>
      </button>

      {modalOpen && (
        <HealthDetailModal
          health={health}
          loading={loading}
          lastChecked={lastChecked}
          onClose={() => setModalOpen(false)}
        />
      )}
    </>
  );
};

export default HealthIndicator;
