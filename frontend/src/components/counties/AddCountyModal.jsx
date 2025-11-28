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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900 bg-opacity-50">
      {/* Modal Container */}
      <div className="relative w-full max-w-2xl max-h-[90vh] bg-white rounded-xl shadow-2xl flex flex-col animate-slide-in">
        {/* Modal Header - Fixed */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-xl font-semibold text-gray-900">Add New County</h3>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 transition-colors rounded-lg hover:text-gray-600 hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body - Scrollable */}
        <div className="flex-1 px-6 py-4 overflow-y-auto custom-scrollbar">
          {/* Progress Steps */}
          <div className="mb-6">
            <div className="flex items-center justify-between">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    step >= i ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
                  }`}>
                    {i}
                  </div>
                  {i < 3 && <div className={`w-16 h-0.5 ${step > i ? 'bg-blue-600' : 'bg-gray-200'}`}></div>}
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-2 text-xs text-gray-600">
              <span>Name</span>
              <span>Credentials</span>
              <span>Test</span>
            </div>
          </div>

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
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Environment</label>
                <select
                  name="accela_environment"
                  value={formData.accela_environment}
                  onChange={handleChange}
                  className="input-field"
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
                  className="input-field"
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
                  className="input-field"
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
                className="btn-secondary w-full"
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
        </div>

        {/* Modal Footer - Fixed */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
          {step > 1 ? (
            <button
              type="button"
              onClick={() => setStep(step - 1)}
              className="btn-secondary"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
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
              className="btn-primary"
            >
              Next
              <ChevronRight className="w-4 h-4 ml-1" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={createCounty.isPending || !testResult?.success}
              className="btn-primary"
            >
              {createCounty.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create County'
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AddCountyModal;
