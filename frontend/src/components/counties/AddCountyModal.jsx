import { useState } from 'react';
import { X, CheckCircle, Loader2, ExternalLink, AlertCircle, Key } from 'lucide-react';
import { useCreateCounty, useGetOAuthUrl, useSetupCountyWithPassword } from '../../hooks/useCounties';

const AddCountyModal = ({ onClose }) => {
  const [step, setStep] = useState(1); // 1: Form, 2: Success/Authorize
  const [authMethod, setAuthMethod] = useState('password'); // 'password' or 'oauth'
  const [formData, setFormData] = useState({
    name: '',
    county_code: '',
  });
  const [createdCounty, setCreatedCounty] = useState(null);
  const [credentials, setCredentials] = useState({
    username: '',
    password: '',
  });

  const createCounty = useCreateCounty();
  const getOAuthUrl = useGetOAuthUrl();
  const setupWithPassword = useSetupCountyWithPassword();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleCredentialChange = (e) => {
    setCredentials({ ...credentials, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const result = await createCounty.mutateAsync(formData);
      // Extract county from {success: true, data: {...}} response
      setCreatedCounty(result.data || result);
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

  const handlePasswordSetup = async (e) => {
    e.preventDefault();
    try {
      await setupWithPassword.mutateAsync({
        id: createdCounty.id,
        credentials: {
          username: credentials.username,
          password: credentials.password,
          scope: 'records',
        },
      });
      // Success! Close modal
      onClose();
    } catch (error) {
      console.error('Failed to setup with password:', error);
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
                      {createdCounty.name} has been created. Choose how you'd like to authorize it below.
                    </p>
                  </div>
                </div>
              </div>

              {/* Auth Method Toggle */}
              <div className="flex gap-2 p-1 bg-gray-100 rounded-lg">
                <button
                  type="button"
                  onClick={() => setAuthMethod('password')}
                  className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    authMethod === 'password'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Key className="h-4 w-4 inline mr-2" />
                  Password (Recommended)
                </button>
                <button
                  type="button"
                  onClick={() => setAuthMethod('oauth')}
                  className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    authMethod === 'oauth'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <ExternalLink className="h-4 w-4 inline mr-2" />
                  OAuth Popup
                </button>
              </div>

              {/* Password Method */}
              {authMethod === 'password' && (
                <div className="space-y-4">
                  {/* Info */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start">
                      <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5 mr-3" />
                      <div className="flex-1 text-sm text-blue-800">
                        <p className="font-medium mb-1">Simpler & More Reliable</p>
                        <p>
                          Enter your Accela credentials once. We'll securely exchange them for access tokens.
                          You'll never need to enter your password again - refresh tokens handle ongoing access.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Credentials Form */}
                  <form onSubmit={handlePasswordSetup} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">
                        Accela Username/Email
                      </label>
                      <input
                        type="email"
                        name="username"
                        value={credentials.username}
                        onChange={handleCredentialChange}
                        placeholder="user@example.com"
                        className="input-field"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">
                        Accela Password
                      </label>
                      <input
                        type="password"
                        name="password"
                        value={credentials.password}
                        onChange={handleCredentialChange}
                        placeholder="••••••••"
                        className="input-field"
                        required
                      />
                      <p className="mt-1.5 text-xs text-gray-500">
                        Your password is sent directly to Accela and never stored
                      </p>
                    </div>

                    {/* Error Message */}
                    {setupWithPassword.error && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                        <div className="flex items-start">
                          <X className="h-5 w-5 text-red-600 mt-0.5 mr-3" />
                          <p className="text-sm text-red-800">
                            {setupWithPassword.error.response?.data?.error || 'Failed to setup county'}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Action Buttons */}
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
                        disabled={setupWithPassword.isPending}
                        className="btn-primary"
                      >
                        {setupWithPassword.isPending ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Connecting...
                          </>
                        ) : (
                          'Connect County'
                        )}
                      </button>
                    </div>
                  </form>
                </div>
              )}

              {/* OAuth Method */}
              {authMethod === 'oauth' && (
                <div className="space-y-4">
                  {/* Info */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start">
                      <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5 mr-3" />
                      <div className="flex-1 text-sm text-blue-800">
                        <p className="font-medium mb-1">OAuth Popup Flow</p>
                        <p>
                          You'll be taken to Accela's login page in a new window where you can log in
                          with your county-specific Accela account.
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
                      Cancel
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
          )}
        </div>
      </div>
    </div>
  );
};

export default AddCountyModal;
