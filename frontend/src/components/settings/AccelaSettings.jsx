import { useState, useEffect } from 'react';
import { Save, CheckCircle, AlertCircle, Loader2, Eye, EyeOff, Key } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsApi } from '../../api/settings';
import { maskApiKey } from '../../utils/formatters';

const AccelaSettings = () => {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    app_id: '',
    app_secret: '',
  });
  const [showAppSecret, setShowAppSecret] = useState(false);
  const [saveResult, setSaveResult] = useState(null);

  const { data: config, isLoading } = useQuery({
    queryKey: ['accela-settings'],
    queryFn: settingsApi.getAccelaSettings,
  });

  const updateSettings = useMutation({
    mutationFn: settingsApi.updateAccelaSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accela-settings'] });
      setSaveResult({ success: true, message: 'Accela credentials saved successfully!' });
      setTimeout(() => setSaveResult(null), 3000);
    },
    onError: (error) => {
      setSaveResult({ success: false, message: error.message || 'Failed to save credentials' });
    },
  });

  useEffect(() => {
    if (config) {
      setFormData({
        app_id: config.app_id || '',
        app_secret: config.app_secret || '',
      });
    }
  }, [config]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaveResult(null);
    try {
      await updateSettings.mutateAsync(formData);
    } catch (error) {
      // Error handled in onError
    }
  };

  if (isLoading) {
    return (
      <div className="card">
        <div className="card-body flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  return (
    <div className="card animate-fade-in">
      {/* Card Header */}
      <div className="card-header">
        <div className="flex items-center space-x-3">
          <div className="flex items-center justify-center w-10 h-10 bg-purple-100 rounded-lg">
            <Key className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Accela API Configuration</h3>
            <p className="text-sm text-gray-600">
              Global credentials shared across all counties
            </p>
          </div>
        </div>
      </div>

      {/* Card Body */}
      <div className="card-body">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* App ID Field */}
          <div>
            <label htmlFor="app_id" className="block text-sm font-medium text-gray-700 mb-1.5">
              Application ID
            </label>
            <input
              type="text"
              name="app_id"
              id="app_id"
              value={formData.app_id}
              onChange={handleChange}
              placeholder="Enter Accela Application ID"
              className="input-field"
            />
            <p className="mt-1.5 text-xs text-gray-500">
              Get your App ID from the Accela Developer Portal
            </p>
          </div>

          {/* App Secret Field */}
          <div>
            <label htmlFor="app_secret" className="block text-sm font-medium text-gray-700 mb-1.5">
              Application Secret
            </label>
            <div className="flex rounded-lg shadow-sm">
              <input
                type={showAppSecret ? 'text' : 'password'}
                name="app_secret"
                id="app_secret"
                value={formData.app_secret}
                onChange={handleChange}
                placeholder="Enter Accela Application Secret"
                className="input-field rounded-r-none flex-1"
              />
              <button
                type="button"
                onClick={() => setShowAppSecret(!showAppSecret)}
                className="inline-flex items-center px-4 py-2 border border-l-0 border-gray-300 bg-gray-50 text-gray-700 rounded-r-lg hover:bg-gray-100 transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                {showAppSecret ? (
                  <>
                    <EyeOff className="h-4 w-4 mr-1.5" />
                    <span className="text-sm font-medium">Hide</span>
                  </>
                ) : (
                  <>
                    <Eye className="h-4 w-4 mr-1.5" />
                    <span className="text-sm font-medium">Show</span>
                  </>
                )}
              </button>
            </div>
            {formData.app_secret && !showAppSecret && (
              <p className="mt-1.5 text-sm text-gray-500">{maskApiKey(formData.app_secret)}</p>
            )}
            <p className="mt-1.5 text-xs text-gray-500">
              These credentials will be used for all counties via OAuth refresh tokens
            </p>
          </div>

          {/* Save Result Alert */}
          {saveResult && (
            <div
              className={`rounded-lg p-4 animate-fade-in ${
                saveResult.success
                  ? 'bg-green-50 border border-green-200'
                  : 'bg-red-50 border border-red-200'
              }`}
            >
              <div className="flex items-start">
                {saveResult.success ? (
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                )}
                <div className="ml-3">
                  <p className={`text-sm font-medium ${
                    saveResult.success ? 'text-green-800' : 'text-red-800'
                  }`}>
                    {saveResult.message}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Action Button */}
          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={updateSettings.isPending || !formData.app_id || !formData.app_secret}
              className="btn-primary"
            >
              {updateSettings.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Credentials
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AccelaSettings;
