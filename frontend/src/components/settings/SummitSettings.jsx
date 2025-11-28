import { useState, useEffect } from 'react';
import { Save, CheckCircle, AlertCircle, Loader2, Eye, EyeOff, Cloud } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { summitApi } from '../../api/summit';
import { maskApiKey } from '../../utils/formatters';

const SummitSettings = () => {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    api_key: '',
    location_id: '',
  });
  const [showApiKey, setShowApiKey] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const { data: config, isLoading } = useQuery({
    queryKey: ['summit-config'],
    queryFn: summitApi.getConfig,
  });

  const updateConfig = useMutation({
    mutationFn: summitApi.updateConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['summit-config'] });
      setTestResult({ success: true, message: 'Settings saved successfully!' });
      setTimeout(() => setTestResult(null), 3000);
    },
  });

  const testConnection = useMutation({
    mutationFn: summitApi.testConnection,
  });

  useEffect(() => {
    if (config) {
      setFormData({
        api_key: config.api_key || '',
        location_id: config.location_id || '',
      });
    }
  }, [config]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleTestConnection = async () => {
    setTestResult(null);
    try {
      await testConnection.mutateAsync();
      setTestResult({ success: true, message: 'Connection successful!' });
    } catch (error) {
      setTestResult({ success: false, message: error.message });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await updateConfig.mutateAsync(formData);
    } catch (error) {
      setTestResult({ success: false, message: error.message });
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
          <div className="flex items-center justify-center w-10 h-10 bg-blue-100 rounded-lg">
            <Cloud className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">The Summit.AI Configuration</h3>
            <p className="text-sm text-gray-600">
              Configure your Summit.AI (HighLevel) CRM integration settings
            </p>
          </div>
        </div>
      </div>

      {/* Card Body */}
      <div className="card-body">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* API Key Field */}
          <div>
            <label htmlFor="api_key" className="block text-sm font-medium text-gray-700 mb-1.5">
              API Key
            </label>
            <div className="flex rounded-lg shadow-sm">
              <input
                type={showApiKey ? 'text' : 'password'}
                name="api_key"
                id="api_key"
                value={formData.api_key}
                onChange={handleChange}
                placeholder="Enter your Summit.AI API key"
                className="input-field rounded-r-none flex-1"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="inline-flex items-center px-4 py-2 border border-l-0 border-gray-300 bg-gray-50 text-gray-700 rounded-r-lg hover:bg-gray-100 transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {showApiKey ? (
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
            {formData.api_key && !showApiKey && (
              <p className="mt-1.5 text-sm text-gray-500">{maskApiKey(formData.api_key)}</p>
            )}
          </div>

          {/* Location ID Field */}
          <div>
            <label htmlFor="location_id" className="block text-sm font-medium text-gray-700 mb-1.5">
              Location ID
            </label>
            <input
              type="text"
              name="location_id"
              id="location_id"
              value={formData.location_id}
              onChange={handleChange}
              placeholder="Enter your Summit.AI Location ID"
              className="input-field"
            />
          </div>

          {/* Test Result Alert */}
          {testResult && (
            <div
              className={`rounded-lg p-4 animate-fade-in ${
                testResult.success
                  ? 'bg-green-50 border border-green-200'
                  : 'bg-red-50 border border-red-200'
              }`}
            >
              <div className="flex items-start">
                {testResult.success ? (
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                )}
                <div className="ml-3">
                  <p className={`text-sm font-medium ${
                    testResult.success ? 'text-green-800' : 'text-red-800'
                  }`}>
                    {testResult.message}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testConnection.isPending || !formData.api_key}
              className="btn-secondary"
            >
              {testConnection.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Testing...
                </>
              ) : (
                <>
                  <Cloud className="h-4 w-4 mr-2" />
                  Test Connection
                </>
              )}
            </button>

            <button
              type="submit"
              disabled={updateConfig.isPending}
              className="btn-primary"
            >
              {updateConfig.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Settings
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SummitSettings;
