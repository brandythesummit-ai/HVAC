import { useState } from 'react';
import { X, ChevronRight, ChevronLeft, CheckCircle, Loader2 } from 'lucide-react';
import { useCreateCounty, useTestCountyConnection } from '../../hooks/useCounties';

const AddCountyModal = ({ onClose }) => {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    name: '',
    accela_environment: 'PROD',
    accela_app_id: '',
    accela_app_secret: '',
  });
  const [testResult, setTestResult] = useState(null);

  const createCounty = useCreateCounty();
  const testConnection = useTestCountyConnection();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleTestConnection = async () => {
    setTestResult(null);
    try {
      await testConnection.mutateAsync(formData);
      setTestResult({ success: true, message: 'Connection successful!' });
    } catch (error) {
      setTestResult({ success: false, message: error.message });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await createCounty.mutateAsync(formData);
      onClose();
    } catch (error) {
      console.error('Failed to create county:', error);
    }
  };

  const canProceedToStep2 = formData.name.trim() !== '';
  const canProceedToStep3 = formData.accela_app_id && formData.accela_app_secret;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={onClose}></div>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Add New County</h3>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
                <X className="h-6 w-6" />
              </button>
            </div>

            {/* Progress Steps */}
            <div className="mb-6">
              <div className="flex items-center justify-between">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      step >= i ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'
                    }`}>
                      {i}
                    </div>
                    {i < 3 && <div className={`w-16 h-0.5 ${step > i ? 'bg-primary-600' : 'bg-gray-200'}`}></div>}
                  </div>
                ))}
              </div>
              <div className="flex justify-between mt-2 text-xs text-gray-600">
                <span>Name</span>
                <span>Credentials</span>
                <span>Test</span>
              </div>
            </div>

            <form onSubmit={handleSubmit}>
              {/* Step 1: County Name */}
              {step === 1 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">County Name</label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      placeholder="e.g., Santa Clara County"
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Environment</label>
                    <select
                      name="accela_environment"
                      value={formData.accela_environment}
                      onChange={handleChange}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                    >
                      <option value="PROD">Production</option>
                      <option value="TEST">Test</option>
                    </select>
                  </div>
                </div>
              )}

              {/* Step 2: Accela Credentials */}
              {step === 2 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Accela App ID</label>
                    <input
                      type="text"
                      name="accela_app_id"
                      value={formData.accela_app_id}
                      onChange={handleChange}
                      placeholder="Your Accela App ID"
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Accela App Secret</label>
                    <input
                      type="password"
                      name="accela_app_secret"
                      value={formData.accela_app_secret}
                      onChange={handleChange}
                      placeholder="Your Accela App Secret"
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                </div>
              )}

              {/* Step 3: Test Connection */}
              {step === 3 && (
                <div className="space-y-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">County Details</h4>
                    <dl className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <dt className="text-gray-600">Name:</dt>
                        <dd className="text-gray-900 font-medium">{formData.name}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-gray-600">Environment:</dt>
                        <dd className="text-gray-900 font-medium">{formData.accela_environment}</dd>
                      </div>
                    </dl>
                  </div>

                  <button
                    type="button"
                    onClick={handleTestConnection}
                    disabled={testConnection.isPending}
                    className="w-full inline-flex items-center justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                  >
                    {testConnection.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Testing...
                      </>
                    ) : (
                      'Test Connection'
                    )}
                  </button>

                  {testResult && (
                    <div className={`rounded-md p-4 ${testResult.success ? 'bg-green-50' : 'bg-red-50'}`}>
                      <div className="flex">
                        {testResult.success ? (
                          <CheckCircle className="h-5 w-5 text-green-400" />
                        ) : (
                          <X className="h-5 w-5 text-red-400" />
                        )}
                        <div className="ml-3">
                          <p className={`text-sm font-medium ${testResult.success ? 'text-green-800' : 'text-red-800'}`}>
                            {testResult.message}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Navigation Buttons */}
              <div className="mt-6 flex justify-between">
                {step > 1 ? (
                  <button
                    type="button"
                    onClick={() => setStep(step - 1)}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                  >
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    Back
                  </button>
                ) : (
                  <div></div>
                )}

                {step < 3 ? (
                  <button
                    type="button"
                    onClick={() => setStep(step + 1)}
                    disabled={(step === 1 && !canProceedToStep2) || (step === 2 && !canProceedToStep3)}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={createCounty.isPending || !testResult?.success}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
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
                )}
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AddCountyModal;
