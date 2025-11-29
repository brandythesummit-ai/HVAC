import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Download, Loader2, AlertCircle } from 'lucide-react';
import { usePullPermits } from '../../hooks/usePermits';
import { formatDate } from '../../utils/formatters';
import PullResultsView from './PullResultsView';
import PermitDetailModal from './PermitDetailModal';

const PullPermitsModal = ({ county, onClose }) => {
  const [formData, setFormData] = useState({
    date_from: '',
    date_to: formatDate(new Date(), 'yyyy-MM-dd'),
    older_than_years: '',
    limit: 100,
    finaled_only: false,
  });
  const [useYearsFilter, setUseYearsFilter] = useState(false);
  const [pullResults, setPullResults] = useState(null);
  const [showResults, setShowResults] = useState(false);
  const [selectedPermit, setSelectedPermit] = useState(null);

  const pullPermits = usePullPermits();
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    let params = {
      limit: parseInt(formData.limit),
      status: formData.finaled_only ? 'Finaled' : undefined,
    };

    if (useYearsFilter && formData.older_than_years) {
      const yearsAgo = new Date();
      yearsAgo.setFullYear(yearsAgo.getFullYear() - parseInt(formData.older_than_years));
      params.date_from = formatDate(yearsAgo, 'yyyy-MM-dd');
      params.date_to = formatDate(new Date(), 'yyyy-MM-dd');
    } else {
      if (formData.date_from) params.date_from = formData.date_from;
      if (formData.date_to) params.date_to = formData.date_to;
    }

    try {
      const response = await pullPermits.mutateAsync({ countyId: county.id, params });

      if (response.success) {
        // Store results and switch to results view
        setPullResults(response.data);
        setShowResults(true);
      }
    } catch (error) {
      console.error('Failed to pull permits:', error);
    }
  };

  const handleGoToLeads = () => {
    navigate('/leads', {
      state: {
        filterByCounty: county.id,
        filterBySyncStatus: 'pending'
      }
    });
    onClose();
  };

  const handleViewDetail = (permit) => {
    setSelectedPermit(permit);
  };

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900 bg-opacity-50 pointer-events-none">
        {/* Modal Container */}
        <div className="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-xl shadow-2xl flex flex-col animate-slide-in pointer-events-auto">
          {/* Modal Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h3 className="text-xl font-semibold text-gray-900">
              {showResults ? `Pull Results - ${county.name}` : `Pull Permits - ${county.name}`}
            </h3>
            <button
              onClick={onClose}
              className="p-1 text-gray-400 transition-colors rounded-lg hover:text-gray-600 hover:bg-gray-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Modal Body */}
          <div className="flex-1 px-6 py-4 overflow-y-auto custom-scrollbar">
            {!showResults ? (
              /* FORM VIEW */
              <form onSubmit={handleSubmit} id="pull-permits-form">
                <div className="space-y-4">
                  {/* Filter Type Toggle */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Filter Type</label>
                    <div className="flex items-center space-x-4">
                      <label className="flex items-center cursor-pointer">
                        <input
                          type="radio"
                          checked={!useYearsFilter}
                          onChange={() => setUseYearsFilter(false)}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                        />
                        <span className="ml-2 text-sm text-gray-700">Date Range</span>
                      </label>
                      <label className="flex items-center cursor-pointer">
                        <input
                          type="radio"
                          checked={useYearsFilter}
                          onChange={() => setUseYearsFilter(true)}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                        />
                        <span className="ml-2 text-sm text-gray-700">Older Than X Years</span>
                      </label>
                    </div>
                  </div>

                  {/* Date Range Inputs */}
                  {!useYearsFilter ? (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
                        <input
                          type="date"
                          name="date_from"
                          value={formData.date_from}
                          onChange={handleChange}
                          className="input-field"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
                        <input
                          type="date"
                          name="date_to"
                          value={formData.date_to}
                          onChange={handleChange}
                          className="input-field"
                        />
                      </div>
                    </div>
                  ) : (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Years Ago</label>
                      <input
                        type="number"
                        name="older_than_years"
                        value={formData.older_than_years}
                        onChange={handleChange}
                        min="1"
                        max="50"
                        placeholder="e.g., 5"
                        className="input-field"
                      />
                      <p className="mt-1.5 text-sm text-gray-500">
                        Pull permits from the last {formData.older_than_years || 'X'} years
                      </p>
                    </div>
                  )}

                  {/* Max Results */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Max Results</label>
                    <select
                      name="limit"
                      value={formData.limit}
                      onChange={handleChange}
                      className="input-field"
                    >
                      <option value="50">50</option>
                      <option value="100">100</option>
                      <option value="250">250</option>
                      <option value="500">500</option>
                      <option value="1000">1000</option>
                    </select>
                  </div>

                  {/* Finaled Only Checkbox */}
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      name="finaled_only"
                      checked={formData.finaled_only}
                      onChange={handleChange}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label className="ml-2 block text-sm text-gray-900">
                      Finaled permits only
                    </label>
                  </div>

                  {/* Error Messages */}
                  {pullPermits.isError && (
                    <div className="rounded-lg bg-red-50 p-4 border border-red-200">
                      <div className="flex">
                        <AlertCircle className="h-5 w-5 text-red-500" />
                        <div className="ml-3">
                          <p className="text-sm font-medium text-red-800">
                            {pullPermits.error.message}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </form>
            ) : (
              /* RESULTS VIEW */
              <PullResultsView
                results={pullResults}
                county={county}
                onClose={onClose}
                onGoToLeads={handleGoToLeads}
                onViewDetail={handleViewDetail}
              />
            )}
          </div>

          {/* Modal Footer - Only show for form view */}
          {!showResults && (
            <div className="flex items-center justify-end px-6 py-4 border-t border-gray-200 bg-gray-50 space-x-3">
              <button
                type="button"
                onClick={onClose}
                disabled={pullPermits.isPending}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                form="pull-permits-form"
                disabled={pullPermits.isPending}
                className="btn-primary"
              >
                {pullPermits.isPending ? (
                  <div className="flex items-center">
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    <div className="flex flex-col items-start">
                      <span className="font-medium">Pulling Permits...</span>
                      <span className="text-xs font-normal text-blue-100 mt-0.5">
                        {useYearsFilter && formData.older_than_years
                          ? `Last ${formData.older_than_years} years`
                          : formData.date_from && formData.date_to
                          ? `${formData.date_from} to ${formData.date_to}`
                          : 'All dates'}
                        {formData.finaled_only ? ' • Finaled only' : ''}
                        {' • Max: ' + formData.limit}
                      </span>
                    </div>
                  </div>
                ) : (
                  <>
                    <Download className="h-4 w-4 mr-2" />
                    Pull Permits
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Permit Detail Modal */}
      {selectedPermit && (
        <PermitDetailModal
          permit={selectedPermit}
          onClose={() => setSelectedPermit(null)}
        />
      )}
    </>
  );
};

export default PullPermitsModal;
