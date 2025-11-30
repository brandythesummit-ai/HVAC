const LeadTierBadge = ({ tier, score }) => {
  const getTierConfig = () => {
    switch (tier) {
      case 'HOT':
        return {
          bgColor: 'bg-red-100',
          textColor: 'text-red-800',
          borderColor: 'border-red-300',
          icon: '🔥'
        };
      case 'WARM':
        return {
          bgColor: 'bg-orange-100',
          textColor: 'text-orange-800',
          borderColor: 'border-orange-300',
          icon: '🌡️'
        };
      case 'COOL':
        return {
          bgColor: 'bg-blue-100',
          textColor: 'text-blue-800',
          borderColor: 'border-blue-300',
          icon: '❄️'
        };
      case 'COLD':
        return {
          bgColor: 'bg-gray-100',
          textColor: 'text-gray-800',
          borderColor: 'border-gray-300',
          icon: '🧊'
        };
      default:
        return {
          bgColor: 'bg-gray-100',
          textColor: 'text-gray-600',
          borderColor: 'border-gray-300',
          icon: '—'
        };
    }
  };

  const config = getTierConfig();

  if (!tier && (score === null || score === undefined)) {
    return <span className="text-sm text-gray-400">—</span>;
  }

  return (
    <div className="space-y-1">
      {score !== null && score !== undefined && (
        <div className="text-sm font-bold text-gray-900">
          Score: {score}
        </div>
      )}
      {tier && (
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium border ${config.bgColor} ${config.textColor} ${config.borderColor}`}
        >
          <span className="mr-1">{config.icon}</span>
          {tier}
        </span>
      )}
    </div>
  );
};

export default LeadTierBadge;
