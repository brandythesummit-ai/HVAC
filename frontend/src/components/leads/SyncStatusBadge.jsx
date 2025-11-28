import { Clock, CheckCircle, XCircle } from 'lucide-react';

const SyncStatusBadge = ({ status }) => {
  const configs = {
    pending: {
      icon: Clock,
      text: 'Pending',
      className: 'bg-yellow-100 text-yellow-800',
      iconColor: 'text-yellow-600',
    },
    synced: {
      icon: CheckCircle,
      text: 'Synced',
      className: 'bg-green-100 text-green-800',
      iconColor: 'text-green-600',
    },
    failed: {
      icon: XCircle,
      text: 'Failed',
      className: 'bg-red-100 text-red-800',
      iconColor: 'text-red-600',
    },
  };

  const config = configs[status] || configs.pending;
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className}`}>
      <Icon className={`h-3 w-3 mr-1 ${config.iconColor}`} />
      {config.text}
    </span>
  );
};

export default SyncStatusBadge;
