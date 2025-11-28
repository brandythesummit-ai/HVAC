import { formatDate, formatCurrency } from '../../utils/formatters';
import SyncStatusBadge from './SyncStatusBadge';

const LeadRow = ({ lead, isSelected, onToggle }) => {
  return (
    <tr className="hover:bg-gray-50 transition-colors duration-150">
      <td className="px-6 py-4 whitespace-nowrap">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggle}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer"
        />
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm font-medium text-gray-900">{lead.owner_name || '-'}</div>
        <div className="text-sm text-gray-500">{lead.owner_phone || '-'}</div>
      </td>
      <td className="px-6 py-4">
        <div className="text-sm text-gray-900">{lead.property_address || '-'}</div>
        <div className="text-sm text-gray-500">{lead.county_name}</div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {formatDate(lead.permit_opened_date)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {lead.year_built || '-'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {lead.square_footage ? `${lead.square_footage.toLocaleString()} sqft` : '-'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
        {formatCurrency(lead.job_value)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <SyncStatusBadge status={lead.summit_sync_status} />
      </td>
    </tr>
  );
};

export default LeadRow;
