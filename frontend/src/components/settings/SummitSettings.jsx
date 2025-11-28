import { useState, useEffect } from 'react';
import { Save, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
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
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="bg-white shadow-sm rounded-lg border border-gray-200">
      <div className="px-4 py-5 sm:p-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900">The Summit.AI Configuration</h3>
        <p className="mt-1 text-sm text-gray-500">
          Configure your Summit.AI (HighLevel) CRM integration settings
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-6">
          <div>
            <label htmlFor="api_key" className="block text-sm font-medium text-gray-700">
              API Key
            </label>
            <div className="mt-1 flex rounded-md shadow-sm">
              <input
                type={showApiKey ? 'text' : 'password'}
                name="api_key"
                id="api_key"
                value={formData.api_key}
                onChange={handleChange}
                placeholder="Enter your Summit.AI API key"
                className="flex-1 min-w-0 block w-full px-3 py-2 rounded-none rounded-l-md border border-gray-300 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="inline-flex items-center px-3 rounded-r-md border border-l-0 border-gray-300 bg-gray-50 text-gray-500 text-sm hover:bg-gray-100"
              >
                {showApiKey ? 'Hide' : 'Show'}
              </button>
            </div>
            {formData.api_key && !showApiKey && (
              <p className="mt-1 text-sm text-gray-500">{maskApiKey(formData.api_key)}</p>
            )}
          </div>

          <div>
            <label htmlFor="location_id" className="block text-sm font-medium text-gray-700">
              Location ID
            </label>
            <input
              type="text"
              name="location_id"
              id="location_id"
              value={formData.location_id}
              onChange={handleChange}
              placeholder="Enter your Summit.AI Location ID"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            />
          </div>

          {testResult && (
            <div className={`rounded-md p-4 ${testResult.success ? 'bg-green-50' : 'bg-red-50'}`}>
              <div className="flex">
                {testResult.success ? (
                  <CheckCircle className="h-5 w-5 text-green-400" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-400" />
                )}
                <div className="ml-3">
                  <p className={`text-sm font-medium ${testResult.success ? 'text-green-800' : 'text-red-800'}`}>
                    {testResult.message}
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center space-x-4">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testConnection.isPending || !formData.api_key}
              className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
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

            <button
              type="submit"
              disabled={updateConfig.isPending}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
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
