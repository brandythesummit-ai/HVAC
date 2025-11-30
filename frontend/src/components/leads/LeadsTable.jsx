import { useState, useEffect } from 'react';
import { Send, Loader2, Settings2, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import LeadRow from './LeadRow';
import ColumnCustomizer from './ColumnCustomizer';
import { useSyncLeadsToSummit, useDeleteLead } from '../../hooks/useLeads';

// Column definitions with metadata
const COLUMN_DEFINITIONS = [
  {
    id: 'select',
    label: 'Select',
    required: true,
    defaultVisible: true,
    description: 'Checkbox for bulk selection',
  },
  {
    id: 'contact',
    label: 'Contact',
    required: false,
    defaultVisible: true,
    description: 'Owner name and phone',
  },
  {
    id: 'address',
    label: 'Address',
    required: false,
    defaultVisible: true,
    description: 'Property address and neighborhood',
  },
  {
    id: 'pipeline',
    label: 'Recommended Pipeline',
    required: false,
    defaultVisible: true,
    description: 'AI-recommended Summit.ai pipeline',
  },
  {
    id: 'hvac_age',
    label: 'HVAC Age',
    required: false,
    defaultVisible: true,
    description: 'Age of HVAC system',
  },
  {
    id: 'score_tier',
    label: 'Score / Tier',
    required: false,
    defaultVisible: true,
    description: 'Lead score and tier classification',
  },
  {
    id: 'contact_info',
    label: 'Contact Completeness',
    required: false,
    defaultVisible: false,
    description: 'Availability of contact information',
  },
  {
    id: 'affluence',
    label: 'Affluence Tier',
    required: false,
    defaultVisible: false,
    description: 'Property value-based affluence classification',
  },
  {
    id: 'lot_size',
    label: 'Lot Size',
    required: false,
    defaultVisible: true,
    description: 'Property lot size in square feet',
  },
  {
    id: 'property_value',
    label: 'Property Value',
    required: false,
    defaultVisible: true,
    description: 'Total assessed property value',
  },
  {
    id: 'year_built',
    label: 'Year Built',
    required: false,
    defaultVisible: false,
    description: 'Year the property was built',
  },
  {
    id: 'status',
    label: 'Sync Status',
    required: true,
    defaultVisible: true,
    description: 'Summit.ai sync status',
  },
];

const STORAGE_KEY = 'hvac_leads_visible_columns';

const LeadsTable = ({ leads, isLoading, onDelete }) => {
  const [selectedLeads, setSelectedLeads] = useState(new Set());
  const [customizerOpen, setCustomizerOpen] = useState(false);
  const [showBulkDeleteConfirm, setShowBulkDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const syncToSummit = useSyncLeadsToSummit();
  const deleteLead = useDeleteLead();

  // Initialize visible columns from localStorage or defaults
  const [visibleColumns, setVisibleColumns] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (e) {
        console.error('Failed to parse stored columns:', e);
      }
    }
    return COLUMN_DEFINITIONS.filter(col => col.defaultVisible).map(col => col.id);
  });

  // Save visible columns to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(visibleColumns));
  }, [visibleColumns]);

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
      const result = await syncToSummit.mutateAsync(Array.from(selectedLeads));

      const syncedCount = result?.data?.synced || 0;
      const failedCount = result?.data?.failed || 0;

      if (syncedCount > 0) {
        toast.success(
          `Successfully synced ${syncedCount} lead${syncedCount > 1 ? 's' : ''} to Summit.AI`
        );
      }

      if (failedCount > 0) {
        toast.error(
          `Failed to sync ${failedCount} lead${failedCount > 1 ? 's' : ''}. Check status column for details.`
        );
      }

      setSelectedLeads(new Set());
    } catch (error) {
      console.error('Failed to sync leads:', error);
      toast.error(`Sync failed: ${error.message || 'Unknown error'}`);
    }
  };

  const handleBulkDelete = async () => {
    setIsDeleting(true);
    const leadIds = Array.from(selectedLeads);
    let successCount = 0;
    let failCount = 0;

    try {
      // Delete each lead sequentially
      for (const leadId of leadIds) {
        try {
          await deleteLead.mutateAsync(leadId);
          successCount++;
        } catch (error) {
          console.error(`Failed to delete lead ${leadId}:`, error);
          failCount++;
        }
      }

      // Show results
      if (successCount > 0) {
        toast.success(
          `Successfully deleted ${successCount} lead${successCount > 1 ? 's' : ''}`
        );
      }

      if (failCount > 0) {
        toast.error(
          `Failed to delete ${failCount} lead${failCount > 1 ? 's' : ''}`
        );
      }

      // Clear selection and close modal
      setSelectedLeads(new Set());
      setShowBulkDeleteConfirm(false);
    } catch (error) {
      console.error('Bulk delete failed:', error);
      toast.error(`Delete failed: ${error.message || 'Unknown error'}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSaveColumns = (newVisibleColumns) => {
    setVisibleColumns(newVisibleColumns);
  };

  if (isLoading) {
    return (
      <div className="card animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  if (!leads || leads.length === 0) {
    return (
      <div className="card animate-fade-in">
        <div className="text-center py-12">
          <p className="text-gray-500">No leads found</p>
        </div>
      </div>
    );
  }

  // Get visible column definitions in order
  const visibleColumnDefs = COLUMN_DEFINITIONS.filter(col =>
    visibleColumns.includes(col.id)
  );

  return (
    <div className="animate-fade-in">
      {/* Action Bar */}
      <div className="mb-4 flex items-center justify-between">
        {selectedLeads.size > 0 ? (
          <div className="flex-1 bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between animate-slide-in">
            <span className="text-sm font-medium text-blue-900">
              {selectedLeads.size} lead{selectedLeads.size > 1 ? 's' : ''} selected
            </span>
            <div className="flex gap-3">
              <button
                onClick={() => setShowBulkDeleteConfirm(true)}
                disabled={isDeleting}
                className="btn-secondary text-red-600 hover:bg-red-50 hover:border-red-300 flex items-center gap-2"
              >
                <Trash2 className="h-4 w-4" />
                Delete Selected
              </button>
              <button
                onClick={handleSyncToSummit}
                disabled={syncToSummit.isPending}
                className="btn-primary"
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
          </div>
        ) : (
          <div className="flex-1" />
        )}

        {/* Customize Columns Button */}
        <button
          onClick={() => setCustomizerOpen(true)}
          className="btn-secondary flex items-center gap-2 ml-4"
        >
          <Settings2 className="h-4 w-4" />
          Customize Columns
        </button>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto custom-scrollbar">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {visibleColumnDefs.map((col) => (
                  <th
                    key={col.id}
                    scope="col"
                    className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider"
                  >
                    {col.id === 'select' ? (
                      <input
                        type="checkbox"
                        checked={selectedLeads.size === leads.length && leads.length > 0}
                        onChange={toggleAll}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer"
                      />
                    ) : (
                      col.label
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {leads.map((lead) => (
                <LeadRow
                  key={lead.id}
                  lead={lead}
                  isSelected={selectedLeads.has(lead.id)}
                  onToggle={() => toggleLead(lead.id)}
                  visibleColumns={visibleColumns}
                  onDelete={onDelete}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Column Customizer Modal */}
      <ColumnCustomizer
        isOpen={customizerOpen}
        onClose={() => setCustomizerOpen(false)}
        columns={COLUMN_DEFINITIONS}
        visibleColumns={visibleColumns}
        onSaveColumns={handleSaveColumns}
      />

      {/* Bulk Delete Confirmation Modal */}
      {showBulkDeleteConfirm && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div
            className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
            onClick={() => !isDeleting && setShowBulkDeleteConfirm(false)}
          />
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="relative bg-white rounded-xl shadow-2xl max-w-md w-full animate-fade-in">
              <div className="px-6 py-4">
                <div className="flex items-start gap-3 mb-4">
                  <div className="flex-shrink-0">
                    <Trash2 className="h-6 w-6 text-red-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Delete {selectedLeads.size} Lead{selectedLeads.size > 1 ? 's' : ''}?
                    </h3>
                    <p className="text-sm text-gray-600 mb-2">
                      Are you sure you want to delete the selected {selectedLeads.size} lead{selectedLeads.size > 1 ? 's' : ''}?
                    </p>
                    <p className="text-xs text-red-600 font-medium">
                      This action cannot be undone.
                    </p>
                  </div>
                </div>
                <div className="flex gap-3 justify-end">
                  <button
                    onClick={() => setShowBulkDeleteConfirm(false)}
                    disabled={isDeleting}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleBulkDelete}
                    disabled={isDeleting}
                    className="btn-primary bg-red-600 hover:bg-red-700 flex items-center gap-2"
                  >
                    {isDeleting ? (
                      <>
                        <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                        Deleting {selectedLeads.size} lead{selectedLeads.size > 1 ? 's' : ''}...
                      </>
                    ) : (
                      <>
                        <Trash2 className="h-4 w-4" />
                        Delete {selectedLeads.size} Lead{selectedLeads.size > 1 ? 's' : ''}
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LeadsTable;
