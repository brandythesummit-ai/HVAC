import SummitSettings from '../components/settings/SummitSettings';
import AccelaSettings from '../components/settings/AccelaSettings';
import { Settings as SettingsIcon } from 'lucide-react';

const SettingsPage = () => {
  return (
    <div className="max-w-4xl animate-fade-in">
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center space-x-3 mb-2">
          <div className="flex items-center justify-center w-10 h-10 bg-blue-100 rounded-lg">
            <SettingsIcon className="w-5 h-5 text-blue-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        </div>
        <p className="text-sm text-gray-600">
          Configure your integrations and platform settings
        </p>
      </div>

      {/* Settings Content */}
      <div className="space-y-6">
        <AccelaSettings />
        <SummitSettings />
      </div>
    </div>
  );
};

export default SettingsPage;
