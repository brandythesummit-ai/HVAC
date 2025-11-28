import SummitSettings from '../components/settings/SummitSettings';

const SettingsPage = () => {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Configure your integrations and platform settings
        </p>
      </div>

      <SummitSettings />
    </div>
  );
};

export default SettingsPage;
