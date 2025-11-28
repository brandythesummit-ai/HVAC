import { Clock, CheckCircle, XCircle } from 'lucide-react';

const SyncStatusBadge = ({ status }) => {
  const configs = {
    pending: {
      icon: Clock,
      text: 'Pending',
      className: 'badge badge-warning',
      iconColor: 'text-yellow-600',
    },
    synced: {
      icon: CheckCircle,
      text: 'Synced',
      className: 'badge badge-success',
      iconColor: 'text-green-600',
    },
    failed: {
      icon: XCircle,
      text: 'Failed',
      className: 'badge badge-error',
      iconColor: 'text-red-600',
    },
  };

  const config = configs[status] || configs.pending;
  const Icon = config.icon;

  return (
    <span className={config.className}>
      <Icon className={`h-3 w-3 mr-1 ${config.iconColor}`} />
      {config.text}
    </span>
  );
};

export default SyncStatusBadge;
