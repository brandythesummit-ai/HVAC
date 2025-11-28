import { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';
import LeadRow from './LeadRow';
import { useSyncLeadsToSummit } from '../../hooks/useLeads';

const LeadsTable = ({ leads, isLoading }) => {
  const [selectedLeads, setSelectedLeads] = useState(new Set());
  const syncToSummit = useSyncLeadsToSummit();

  const toggleLead = (leadId) => {
    const newSelected = new Set(selectedLeads);
    if (newSelected.has(leadId)) {
      newSelected.delete(leadId);
    } else {
      newSelected.add(leadId);
    }
    setSelectedLeads(newSelected);
  };

  const toggleAll = () => {
    if (selectedLeads.size === leads.length) {
      setSelectedLeads(new Set());
    } else {
      setSelectedLeads(new Set(leads.map(l => l.id)));
    }
  };

  const handleSyncToSummit = async () => {
    try {
      await syncToSummit.mutateAsync(Array.from(selectedLeads));
      setSelectedLeads(new Set());
    } catch (error) {
      console.error('Failed to sync leads:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!leads || leads.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No leads found</p>
      </div>
    );
  }

  return (
    <div>
      {/* Action Bar */}
      {selectedLeads.size > 0 && (
        <div className="mb-4 bg-primary-50 border border-primary-200 rounded-lg p-4 flex items-center justify-between">
          <span className="text-sm font-medium text-primary-900">
            {selectedLeads.size} lead{selectedLeads.size > 1 ? 's' : ''} selected
          </span>
          <button
            onClick={handleSyncToSummit}
            disabled={syncToSummit.isPending}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
          >
            {syncToSummit.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Syncing...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Send to Summit.AI
              </>
            )}
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <input
                  type="checkbox"
                  checked={selectedLeads.size === leads.length && leads.length > 0}
                  onChange={toggleAll}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Contact
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Address
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Permit Date
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Year Built
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Sq Ft
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Job Value
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {leads.map((lead) => (
              <LeadRow
                key={lead.id}
                lead={lead}
                isSelected={selectedLeads.has(lead.id)}
                onToggle={() => toggleLead(lead.id)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LeadsTable;
