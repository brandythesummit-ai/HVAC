import { useState, useMemo, useEffect } from 'react';
import { Search, Loader2, AlertCircle, MapPin } from 'lucide-react';
import { useCounties } from '../hooks/useCounties';
import StateSection from '../components/counties/StateSection';
import CountyDetailPanel from '../components/counties/CountyDetailPanel';

export default function CountiesPage() {
  const { data: allCounties, isLoading, error } = useCounties();
  const [expandedStates, setExpandedStates] = useState(new Set(['FL'])); // FL expanded by default
  const [selectedCounty, setSelectedCounty] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Group counties by state and sort alphabetically
  const countiesByState = useMemo(() => {
    if (!allCounties) return {};
    const grouped = allCounties.reduce((acc, county) => {
      const state = county.state || 'Unknown';
      if (!acc[state]) acc[state] = [];
      acc[state].push(county);
      return acc;
    }, {});
    // Sort counties within each state alphabetically
    Object.keys(grouped).forEach(state => {
      grouped[state].sort((a, b) => a.name.localeCompare(b.name));
    });
    return grouped;
  }, [allCounties]);

  // Calculate state metrics
  const stateMetrics = useMemo(() => {
    const metrics = {};
    Object.entries(countiesByState).forEach(([state, counties]) => {
      metrics[state] = {
        total: counties.length,
        authorized: counties.filter(c => c.oauth_authorized).length,
        totalLeads: counties.reduce((sum, c) => sum + (c.lead_count || 0), 0),
        lastPull: counties.reduce((latest, c) => {
          const pullTime = c.last_pull_at ? new Date(c.last_pull_at) : null;
          return pullTime && (!latest || pullTime > latest) ? pullTime : latest;
        }, null)
      };
    });
    return metrics;
  }, [countiesByState]);

  // Filter by search
  const filteredStates = useMemo(() => {
    if (!searchQuery.trim()) return Object.keys(countiesByState).sort();

    const query = searchQuery.toLowerCase();
    return Object.keys(countiesByState).filter(state => {
      // Match state name or any county in state
      if (state.toLowerCase().includes(query)) return true;
      return countiesByState[state].some(c =>
        c.name.toLowerCase().includes(query)
      );
    }).sort();
  }, [countiesByState, searchQuery]);

  // Sync selectedCounty with updated allCounties data
  // This ensures the panel shows fresh data after mutations invalidate queries
  useEffect(() => {
    if (selectedCounty && allCounties) {
      const updatedCounty = allCounties.find(c => c.id === selectedCounty.id);
      if (updatedCounty) {
        // Only update if data actually changed (prevents infinite loops)
        const hasChanged = JSON.stringify(updatedCounty) !== JSON.stringify(selectedCounty);
        if (hasChanged) {
          setSelectedCounty(updatedCounty);
        }
      }
    }
  }, [allCounties, selectedCounty]);

  const toggleState = (state) => {
    setExpandedStates(prev => {
      const next = new Set(prev);
      if (next.has(state)) {
        next.delete(state);
      } else {
        next.add(state);
      }
      return next;
    });
  };

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
    <div className="flex h-screen">
      {/* Main content area */}
      <div className={`flex-1 overflow-hidden ${selectedCounty ? 'pr-96' : ''} transition-all duration-300`}>
        {/* Header */}
        <div className="p-6 border-b bg-white">
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Coverage Dashboard</h1>
          <p className="text-sm text-gray-500 mb-4">
            Monitor county permit sources and lead pulling health across all states
          </p>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search states or counties..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* States list */}
        <div className="overflow-y-auto h-[calc(100vh-188px)]">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : filteredStates.length > 0 ? (
            filteredStates.map(state => (
              <StateSection
                key={state}
                state={state}
                counties={countiesByState[state]}
                metrics={stateMetrics[state]}
                isExpanded={expandedStates.has(state)}
                onToggle={() => toggleState(state)}
                onCountySelect={setSelectedCounty}
                selectedCountyId={selectedCounty?.id}
              />
            ))
          ) : searchQuery ? (
            <div className="flex flex-col items-center justify-center h-64 text-gray-500">
              <Search className="h-12 w-12 mb-3 text-gray-300" />
              <p className="text-sm">No counties found matching "{searchQuery}"</p>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-gray-500">
              <MapPin className="h-12 w-12 mb-3 text-gray-300" />
              <p className="text-sm">No counties configured yet</p>
            </div>
          )}
        </div>
      </div>

      {/* Detail panel */}
      {selectedCounty && (
        <CountyDetailPanel
          county={selectedCounty}
          onClose={() => setSelectedCounty(null)}
        />
      )}
    </div>
  );
}
