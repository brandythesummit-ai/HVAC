import { useState } from 'react';
import { X, FileText, Code } from 'lucide-react';
import { formatDate, formatCurrency } from '../../utils/formatters';

const PermitDetailModal = ({ permit, onClose }) => {
  const [activeTab, setActiveTab] = useState('summary');

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-gray-900 bg-opacity-50">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-xl shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-xl font-semibold text-gray-900">
            Permit Details - {permit.accela_record_id}
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="flex px-6">
            <button
              onClick={() => setActiveTab('summary')}
              className={`px-4 py-3 text-sm font-medium border-b-2 ${
                activeTab === 'summary'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <FileText className="w-4 h-4 inline mr-2" />
              Summary
            </button>
            <button
              onClick={() => setActiveTab('raw')}
              className={`px-4 py-3 text-sm font-medium border-b-2 ${
                activeTab === 'raw'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Code className="w-4 h-4 inline mr-2" />
              Raw Accela Data
            </button>
          </nav>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-6 custom-scrollbar">
          {activeTab === 'summary' ? (
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">Owner Name</dt>
                <dd className="mt-1 text-sm text-gray-900">{permit.owner_name || '-'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Owner Phone</dt>
                <dd className="mt-1 text-sm text-gray-900">{permit.owner_phone || '-'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Owner Email</dt>
                <dd className="mt-1 text-sm text-gray-900">{permit.owner_email || '-'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Accela Record ID</dt>
                <dd className="mt-1 text-sm text-gray-900 font-mono">{permit.accela_record_id}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-sm font-medium text-gray-500">Property Address</dt>
                <dd className="mt-1 text-sm text-gray-900">{permit.property_address || '-'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Permit Type</dt>
                <dd className="mt-1 text-sm text-gray-900">{permit.permit_type || '-'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Status</dt>
                <dd className="mt-1 text-sm text-gray-900">{permit.status || '-'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Opened Date</dt>
                <dd className="mt-1 text-sm text-gray-900">{formatDate(permit.opened_date)}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Job Value</dt>
                <dd className="mt-1 text-sm text-gray-900">{formatCurrency(permit.job_value)}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Year Built</dt>
                <dd className="mt-1 text-sm text-gray-900">{permit.year_built || '-'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Square Footage</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {permit.square_footage ? `${permit.square_footage.toLocaleString()} sqft` : '-'}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Property Value</dt>
                <dd className="mt-1 text-sm text-gray-900">{formatCurrency(permit.property_value)}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Lot Size</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {permit.lot_size ? `${permit.lot_size.toLocaleString()} sqft` : '-'}
                </dd>
              </div>
              <div className="col-span-2">
                <dt className="text-sm font-medium text-gray-500">Description</dt>
                <dd className="mt-1 text-sm text-gray-900">{permit.description || '-'}</dd>
              </div>
            </dl>
          ) : (
            <div className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-auto">
              <pre className="text-xs whitespace-pre-wrap font-mono">
                {JSON.stringify(permit.raw_data, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button onClick={onClose} className="btn-primary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default PermitDetailModal;
