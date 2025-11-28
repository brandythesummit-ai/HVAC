import { useState } from 'react';
import { X, Download, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { usePullPermits } from '../../hooks/usePermits';
import { formatDate } from '../../utils/formatters';

const PullPermitsModal = ({ county, onClose }) => {
  const [formData, setFormData] = useState({
    date_from: '',
    date_to: formatDate(new Date(), 'yyyy-MM-dd'),
    older_than_years: '',
    limit: 100,
    finaled_only: false,
  });
  const [useYearsFilter, setUseYearsFilter] = useState(false);

  const pullPermits = usePullPermits();

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
      await pullPermits.mutateAsync({ countyId: county.id, params });
      onClose();
    } catch (error) {
      console.error('Failed to pull permits:', error);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={onClose}></div>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <form onSubmit={handleSubmit}>
            <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">
                  Pull Permits - {county.name}
                </h3>
                <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-500">
                  <X className="h-6 w-6" />
                </button>
              </div>

              <div className="space-y-4">
                {/* Filter Type Toggle */}
                <div className="flex items-center space-x-4">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      checked={!useYearsFilter}
                      onChange={() => setUseYearsFilter(false)}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
                    />
                    <span className="ml-2 text-sm text-gray-700">Date Range</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      checked={useYearsFilter}
                      onChange={() => setUseYearsFilter(true)}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
                    />
                    <span className="ml-2 text-sm text-gray-700">Older Than X Years</span>
                  </label>
                </div>

                {/* Date Range Inputs */}
                {!useYearsFilter ? (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">From Date</label>
                      <input
                        type="date"
                        name="date_from"
                        value={formData.date_from}
                        onChange={handleChange}
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">To Date</label>
                      <input
                        type="date"
                        name="date_to"
                        value={formData.date_to}
                        onChange={handleChange}
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                      />
                    </div>
                  </div>
                ) : (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Years Ago</label>
                    <input
                      type="number"
                      name="older_than_years"
                      value={formData.older_than_years}
                      onChange={handleChange}
                      min="1"
                      max="50"
                      placeholder="e.g., 5"
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                    />
                    <p className="mt-1 text-sm text-gray-500">
                      Pull permits from the last {formData.older_than_years || 'X'} years
                    </p>
                  </div>
                )}

                {/* Max Results */}
                <div>
                  <label className="block text-sm font-medium text-gray-700">Max Results</label>
                  <select
                    name="limit"
                    value={formData.limit}
                    onChange={handleChange}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary-500 focus:border-primary-500"
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
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label className="ml-2 block text-sm text-gray-900">
                    Finaled permits only
                  </label>
                </div>

                {/* Status Messages */}
                {pullPermits.isSuccess && (
                  <div className="rounded-md bg-green-50 p-4">
                    <div className="flex">
                      <CheckCircle className="h-5 w-5 text-green-400" />
                      <div className="ml-3">
                        <p className="text-sm font-medium text-green-800">
                          Permits pulled successfully!
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {pullPermits.isError && (
                  <div className="rounded-md bg-red-50 p-4">
                    <div className="flex">
                      <AlertCircle className="h-5 w-5 text-red-400" />
                      <div className="ml-3">
                        <p className="text-sm font-medium text-red-800">
                          {pullPermits.error.message}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Footer Buttons */}
            <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
              <button
                type="submit"
                disabled={pullPermits.isPending}
                className="w-full inline-flex justify-center items-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-primary-600 text-base font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {pullPermits.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Pulling...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4 mr-2" />
                    Pull Permits
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={onClose}
                disabled={pullPermits.isPending}
                className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default PullPermitsModal;
