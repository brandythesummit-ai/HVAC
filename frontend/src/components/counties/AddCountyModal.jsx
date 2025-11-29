import { useState } from 'react';
import { X, CheckCircle, Loader2, ExternalLink, AlertCircle } from 'lucide-react';
import { useCreateCounty, useGetOAuthUrl } from '../../hooks/useCounties';

const AddCountyModal = ({ onClose }) => {
  const [step, setStep] = useState(1); // 1: Form, 2: Success/Authorize
  const [formData, setFormData] = useState({
    name: '',
    county_code: '',
  });
  const [createdCounty, setCreatedCounty] = useState(null);

  const createCounty = useCreateCounty();
  const getOAuthUrl = useGetOAuthUrl();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const result = await createCounty.mutateAsync(formData);
      setCreatedCounty(result);
      setStep(2);
    } catch (error) {
      console.error('Failed to create county:', error);
    }
  };

  const handleAuthorize = async () => {
    try {
      const { authorization_url } = await getOAuthUrl.mutateAsync(createdCounty.id);
      // Open OAuth URL in new window
      window.open(authorization_url, '_blank', 'width=600,height=700');
      // Close modal after opening OAuth window
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (error) {
      console.error('Failed to get OAuth URL:', error);
    }
  };

  const canSubmit = formData.name.trim() !== '' && formData.county_code.trim() !== '';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900 bg-opacity-50">
      {/* Modal Container */}
      <div className="relative w-full max-w-lg bg-white rounded-xl shadow-2xl animate-slide-in">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-xl font-semibold text-gray-900">Add New County</h3>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 transition-colors rounded-lg hover:text-gray-600 hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="px-6 py-6">
          {step === 1 && (
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Info Alert */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start">
                  <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5 mr-3" />
                  <div className="flex-1">
                    <p className="text-sm text-blue-800">
                      Enter the county information below. After creating the county, you'll authorize it with your Accela account.
                    </p>
                  </div>
                </div>
              </div>

              {/* County Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  County Name
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="e.g., Nassau County"
                  className="input-field"
                  autoFocus
                />
                <p className="mt-1.5 text-xs text-gray-500">
                  The display name for this county
                </p>
              </div>

              {/* County Code */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Accela County Code
                </label>
                <input
                  type="text"
                  name="county_code"
                  value={formData.county_code}
                  onChange={handleChange}
                  placeholder="e.g., ISLANDERNC"
                  className="input-field"
                />
                <p className="mt-1.5 text-xs text-gray-500">
                  The Accela agency code for this county (all caps)
                </p>
              </div>

              {/* Error Message */}
              {createCounty.error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-start">
                    <X className="h-5 w-5 text-red-600 mt-0.5 mr-3" />
                    <p className="text-sm text-red-800">
                      {createCounty.error.message || 'Failed to create county'}
                    </p>
                  </div>
                </div>
              )}

              {/* Submit Button */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!canSubmit || createCounty.isPending}
                  className="btn-primary"
                >
                  {createCounty.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Create County'
                  )}
                </button>
              </div>
            </form>
          )}

          {step === 2 && createdCounty && (
            <div className="space-y-6">
              {/* Success Message */}
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-start">
                  <CheckCircle className="h-6 w-6 text-green-600 mt-0.5 mr-3" />
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-green-900 mb-1">
                      County Created Successfully!
                    </h4>
                    <p className="text-sm text-green-800">
                      {createdCounty.name} has been created. Now authorize it with your Accela account to start pulling permit data.
                    </p>
                  </div>
                </div>
              </div>

              {/* County Details */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-3">County Details</h4>
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-600">Name:</dt>
                    <dd className="text-gray-900 font-medium">{createdCounty.name}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-600">County Code:</dt>
                    <dd className="text-gray-900 font-medium font-mono">{createdCounty.county_code}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-600">Status:</dt>
                    <dd className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                      Pending Authorization
                    </dd>
                  </div>
                </dl>
              </div>

              {/* Authorization Instructions */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start">
                  <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5 mr-3" />
                  <div className="flex-1 text-sm text-blue-800">
                    <p className="font-medium mb-1">Next Step: Authorize with Accela</p>
                    <p>
                      Click "Authorize with Accela" below. You'll be taken to Accela's login page where you can log in with your county-specific Accela account.
                    </p>
                  </div>
                </div>
              </div>

              {/* Error Message */}
              {getOAuthUrl.error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-start">
                    <X className="h-5 w-5 text-red-600 mt-0.5 mr-3" />
                    <p className="text-sm text-red-800">
                      {getOAuthUrl.error.message || 'Failed to get authorization URL'}
                    </p>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="btn-secondary"
                >
                  Do This Later
                </button>
                <button
                  type="button"
                  onClick={handleAuthorize}
                  disabled={getOAuthUrl.isPending}
                  className="btn-primary"
                >
                  {getOAuthUrl.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Loading...
                    </>
                  ) : (
                    <>
                      Authorize with Accela
                      <ExternalLink className="h-4 w-4 ml-2" />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AddCountyModal;
