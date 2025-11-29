import { useState } from 'react';
import { Download, Filter, Users, Eye } from 'lucide-react';
import { formatDate, formatCurrency } from '../../utils/formatters';

const StatCard = ({ label, value, icon }) => (
  <div className="bg-white border border-gray-200 rounded-lg p-4">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-gray-600">{label}</p>
        <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      </div>
      <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg">
        {icon}
      </div>
    </div>
  </div>
);

const PullResultsView = ({ results, county, onClose, onGoToLeads, onViewDetail }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  const totalPages = Math.ceil((results.permits?.length || 0) / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const currentPermits = results.permits?.slice(startIndex, endIndex) || [];

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          label="Total Permits Pulled"
          value={results.total_pulled || 0}
          icon={<Download className="w-6 h-6 text-blue-600" />}
        />
        <StatCard
          label="HVAC Permits"
          value={results.hvac_permits || 0}
          icon={<Filter className="w-6 h-6 text-blue-600" />}
        />
        <StatCard
          label="Leads Created"
          value={results.leads_created || 0}
          icon={<Users className="w-6 h-6 text-blue-600" />}
        />
      </div>

      {/* Results Table */}
      {currentPermits.length > 0 ? (
        <div className="card overflow-hidden">
          <div className="card-header">
            <h4 className="text-lg font-semibold text-gray-900">
              Leads Created ({results.permits.length} total)
            </h4>
          </div>
          <div className="overflow-x-auto custom-scrollbar">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Owner</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Address</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Permit Date</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Year Built</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Job Value</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {currentPermits.map((permit) => (
                  <tr key={permit.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{permit.owner_name || '-'}</div>
                      <div className="text-sm text-gray-500">{permit.owner_phone || '-'}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">{permit.property_address || '-'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(permit.opened_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {permit.year_built || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {formatCurrency(permit.job_value)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={() => onViewDetail(permit)}
                        className="text-blue-600 hover:text-blue-800 font-medium flex items-center"
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Showing {startIndex + 1} to {Math.min(endIndex, results.permits.length)} of {results.permits.length} results
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="btn-secondary disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="btn-secondary disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card">
          <div className="card-body text-center py-12">
            <p className="text-gray-500">No HVAC permits found. Try adjusting your filters.</p>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3 justify-end">
        <button onClick={onClose} className="btn-secondary">
          Close
        </button>
        <button onClick={onGoToLeads} className="btn-primary">
          Go to Leads Page →
        </button>
      </div>
    </div>
  );
};

export default PullResultsView;
