import { useState } from 'react';
import { Plus, Loader2, AlertCircle } from 'lucide-react';
import { useCounties } from '../hooks/useCounties';
import CountyCard from '../components/counties/CountyCard';
import AddCountyModal from '../components/counties/AddCountyModal';

const CountiesPage = () => {
  const [showAddModal, setShowAddModal] = useState(false);
  const { data: counties, isLoading, error } = useCounties();

  if (error) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <div className="flex">
          <AlertCircle className="h-5 w-5 text-red-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error loading counties</h3>
            <p className="mt-2 text-sm text-red-700">{error.message}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="sm:flex sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Counties</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your county connections and pull permits from Accela
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add County
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        </div>
      ) : counties && counties.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {counties.map((county) => (
            <CountyCard key={county.id} county={county} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
          <Plus className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No counties</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by adding your first county.</p>
          <div className="mt-6">
            <button
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add County
            </button>
          </div>
        </div>
      )}

      {showAddModal && <AddCountyModal onClose={() => setShowAddModal(false)} />}
    </div>
  );
};

export default CountiesPage;
