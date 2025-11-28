import { useState } from 'react';
import { Plus, Loader2, AlertCircle, MapPin } from 'lucide-react';
import { useCounties } from '../hooks/useCounties';
import CountyCard from '../components/counties/CountyCard';
import AddCountyModal from '../components/counties/AddCountyModal';

const CountiesPage = () => {
  const [showAddModal, setShowAddModal] = useState(false);
  const { data: counties, isLoading, error } = useCounties();

  if (error) {
    return (
      <div className="card animate-fade-in">
        <div className="card-body">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
            <div className="ml-3">
              <h3 className="text-sm font-semibold text-red-800">Error loading counties</h3>
              <p className="mt-1 text-sm text-red-700">{error.message}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-sm text-gray-500">
            Manage your county connections and pull permits from Accela
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn-primary"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add County
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      ) : counties && counties.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {counties.map((county) => (
            <CountyCard key={county.id} county={county} />
          ))}
        </div>
      ) : (
        <div className="card animate-slide-in">
          <div className="card-body text-center py-12">
            <div className="flex items-center justify-center w-16 h-16 mx-auto bg-gray-100 rounded-full mb-4">
              <MapPin className="h-8 w-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">No counties</h3>
            <p className="mt-1 text-sm text-gray-500">Get started by adding your first county.</p>
            <div className="mt-6">
              <button
                onClick={() => setShowAddModal(true)}
                className="btn-primary"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add County
              </button>
            </div>
          </div>
        </div>
      )}

      {showAddModal && <AddCountyModal onClose={() => setShowAddModal(false)} />}
    </div>
  );
};

export default CountiesPage;
