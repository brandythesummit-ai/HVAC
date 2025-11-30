import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Home, Calendar, DollarSign, Ruler, MapPin, FileText, Loader2, AlertCircle } from 'lucide-react';
import { propertiesApi } from '../api/properties';
import { formatDate, formatCurrency } from '../utils/formatters';
import LeadTierBadge from '../components/leads/LeadTierBadge';

const PropertyDetailPage = () => {
  const { propertyId } = useParams();
  const navigate = useNavigate();
  const [property, setProperty] = useState(null);
  const [permits, setPermits] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPropertyData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Fetch property details
        const propertyResponse = await propertiesApi.getProperty(propertyId);
        setProperty(propertyResponse);

        // Fetch permits for this property
        const permitsResponse = await propertiesApi.getPropertyPermits(propertyId);
        setPermits(permitsResponse.permits || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    if (propertyId) {
      fetchPropertyData();
    }
  }, [propertyId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card bg-red-50 border-red-200 animate-fade-in">
        <div className="card-body">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-semibold text-red-800">Error loading property</h3>
              <p className="mt-2 text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!property) {
    return (
      <div className="card animate-fade-in">
        <div className="text-center py-12">
          <p className="text-gray-500">Property not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center text-sm text-gray-600 hover:text-gray-900 transition-colors"
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back
      </button>

      {/* Property Header */}
      <div className="card animate-fade-in">
        <div className="card-header">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg">
                <Home className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{property.normalized_address}</h1>
                <p className="text-sm text-gray-500 mt-1">Property Details & HVAC History</p>
              </div>
            </div>
            <LeadTierBadge tier={property.lead_tier} score={property.lead_score} />
          </div>
        </div>

        <div className="card-body">
          {/* Property Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
            <div className="bg-purple-50 rounded-lg p-4">
              <div className="flex items-center mb-2">
                <Calendar className="h-5 w-5 text-purple-600 mr-2" />
                <span className="text-sm font-medium text-purple-900">HVAC Age</span>
              </div>
              <p className="text-2xl font-bold text-purple-900">
                {property.hvac_age_years !== null ? `${property.hvac_age_years} years` : '—'}
              </p>
              {property.most_recent_hvac_date && (
                <p className="text-xs text-purple-700 mt-1">
                  Last installed: {formatDate(property.most_recent_hvac_date)}
                </p>
              )}
            </div>

            <div className="bg-green-50 rounded-lg p-4">
              <div className="flex items-center mb-2">
                <DollarSign className="h-5 w-5 text-green-600 mr-2" />
                <span className="text-sm font-medium text-green-900">Property Value</span>
              </div>
              <p className="text-2xl font-bold text-green-900">
                {formatCurrency(property.total_property_value)}
              </p>
            </div>

            <div className="bg-orange-50 rounded-lg p-4">
              <div className="flex items-center mb-2">
                <Ruler className="h-5 w-5 text-orange-600 mr-2" />
                <span className="text-sm font-medium text-orange-900">Lot Size</span>
              </div>
              <p className="text-2xl font-bold text-orange-900">
                {property.lot_size_sqft ? `${property.lot_size_sqft.toLocaleString()}` : '—'}
              </p>
              {property.lot_size_sqft && (
                <p className="text-xs text-orange-700 mt-1">sqft</p>
              )}
            </div>

            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center mb-2">
                <FileText className="h-5 w-5 text-blue-600 mr-2" />
                <span className="text-sm font-medium text-blue-900">Total Permits</span>
              </div>
              <p className="text-2xl font-bold text-blue-900">{property.total_hvac_permits || 0}</p>
            </div>
          </div>

          {/* Owner & Property Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Owner Info */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Owner Information</h3>
              <dl className="space-y-2">
                <div>
                  <dt className="text-xs text-gray-500">Name</dt>
                  <dd className="text-sm font-medium text-gray-900">{property.owner_name || '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Phone</dt>
                  <dd className="text-sm font-medium text-gray-900">{property.owner_phone || '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Email</dt>
                  <dd className="text-sm font-medium text-gray-900">{property.owner_email || '—'}</dd>
                </div>
              </dl>
            </div>

            {/* Property Info */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Property Information</h3>
              <dl className="space-y-2">
                <div>
                  <dt className="text-xs text-gray-500">Parcel Number</dt>
                  <dd className="text-sm font-medium text-gray-900">{property.parcel_number || '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Year Built</dt>
                  <dd className="text-sm font-medium text-gray-900">{property.year_built || '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">City</dt>
                  <dd className="text-sm font-medium text-gray-900">{property.city || '—'}</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* Permit History */}
      <div className="card animate-fade-in">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-gray-900">HVAC Permit History</h2>
          <p className="text-sm text-gray-500 mt-1">
            All HVAC permits for this property ({permits.length} total)
          </p>
        </div>

        <div className="card-body">
          {permits.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No permit history available
            </div>
          ) : (
            <div className="space-y-4">
              {permits.map((permit, index) => (
                <div
                  key={permit.id || index}
                  className={`border rounded-lg p-4 ${
                    permit.id === property.most_recent_hvac_permit_id
                      ? 'border-blue-300 bg-blue-50'
                      : 'border-gray-200 bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-gray-900">{permit.permit_type || permit.description}</h3>
                        {permit.id === property.most_recent_hvac_permit_id && (
                          <span className="badge badge-info text-xs">Most Recent</span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        Permit #{permit.custom_id || permit.accela_record_id}
                      </p>
                    </div>
                    <span className="text-sm font-medium text-gray-700">
                      {formatDate(permit.opened_date)}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <dt className="text-xs text-gray-500">Status</dt>
                      <dd className="font-medium text-gray-900">{permit.status || '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-gray-500">Job Value</dt>
                      <dd className="font-medium text-gray-900">{formatCurrency(permit.job_value)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-gray-500">Description</dt>
                      <dd className="font-medium text-gray-900">{permit.description || '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-gray-500">Neighborhood</dt>
                      <dd className="font-medium text-gray-900">{permit.neighborhood || '—'}</dd>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PropertyDetailPage;
