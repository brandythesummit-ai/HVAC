import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { leadsApi } from '../api/leads';

// The backend returns properties as a nested relation:
//   { id, lead_tier, properties: { normalized_address, latitude, longitude, owner_name, ... } }
// The frontend (MapPage, ListPage, DetailSheet, PlanForTodayPage) reads
// the property fields as if they were flat on the lead. Flatten here so
// every consumer gets the same shape without caring about the join.
function flattenLead(lead) {
  if (!lead) return lead;
  const p = lead.properties || {};
  return {
    ...lead,
    // Build a display-friendly property_address. Prefer the normalized
    // form ("14901 PERRIWINKLE PLACE TAMPA FL 33625") since it's already
    // formatted; fall back to street_number+street_name+suffix if not set.
    property_address: p.normalized_address
      || [p.street_number, p.street_name, p.street_suffix].filter(Boolean).join(' ')
      || null,
    // Map/ListPage read these as flat fields
    latitude: p.latitude,
    longitude: p.longitude,
    owner_name: p.owner_name,
    owner_phone: p.owner_phone,
    owner_email: p.owner_email,
    hvac_age_years: p.hvac_age_years,
    year_built: p.year_built,
    total_hvac_permits: p.total_hvac_permits,
    most_recent_hvac_date: p.most_recent_hvac_date,
    zip_code: p.zip_code,
    city: p.city,
  };
}

export const useLeads = (params = {}) => {
  return useQuery({
    queryKey: ['leads', params],
    queryFn: async () => {
      const data = await leadsApi.getAll(params);
      // API returns { leads: [...], count, total, limit, offset }
      if (data && Array.isArray(data.leads)) {
        return { ...data, leads: data.leads.map(flattenLead) };
      }
      // Tolerate older shapes
      if (Array.isArray(data)) return data.map(flattenLead);
      return data;
    },
  });
};

export const useCreateLeadsFromPermits = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: leadsApi.createFromPermits,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
};

export const useUpdateLeadNotes = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, notes }) => leadsApi.updateNotes(id, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
};

export const useSyncLeadsToSummit = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: leadsApi.syncToSummit,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
};

export const useDeleteLead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: leadsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
};

// M19: transition a lead through the state machine. Triggers cooldown
// computation server-side + optional GHL push on INTERESTED.
export const useUpdateLeadStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, newStatus, note }) =>
      leadsApi.updateStatus(id, { newStatus, note }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
};
