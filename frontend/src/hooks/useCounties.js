import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { countiesApi } from '../api/counties';

export const useCounties = () => {
  return useQuery({
    queryKey: ['counties'],
    queryFn: countiesApi.getAll,
  });
};

export const useCounty = (id) => {
  return useQuery({
    queryKey: ['counties', id],
    queryFn: () => countiesApi.getById(id),
    enabled: !!id,
  });
};

export const useCreateCounty = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: countiesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['counties'],
        refetchType: 'all'
      });
    },
  });
};

export const useUpdateCounty = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => countiesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['counties'],
        refetchType: 'all'
      });
    },
  });
};

export const useDeleteCounty = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: countiesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['counties'],
        refetchType: 'all'
      });
    },
  });
};

export const useTestCountyConnection = () => {
  return useMutation({
    mutationFn: countiesApi.testConnection,
  });
};

export const useGetOAuthUrl = () => {
  return useMutation({
    mutationFn: countiesApi.getOAuthUrl,
  });
};

export const useSetupCountyWithPassword = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, credentials }) => countiesApi.setupWithPassword(id, credentials),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['counties'],
        refetchType: 'all'
      });
    },
  });
};

export const useCountyMetrics = (id) => {
  return useQuery({
    queryKey: ['counties', id, 'metrics'],
    queryFn: () => countiesApi.getMetrics(id),
    enabled: !!id,
  });
};

export const useCountyPullStatus = (id) => {
  return useQuery({
    queryKey: ['counties', id, 'pull-status'],
    queryFn: () => countiesApi.getPullStatus(id),
    enabled: !!id,
    refetchInterval: (query) => {
      // React Query v5: callback receives query object, data is in query.state.data
      const data = query.state.data;

      // Poll every 5 seconds if:
      // 1. Has active job with progress, OR
      // 2. Has years_status with any "in_progress" year, OR
      // 3. Has start_year set but pull not completed (job just started)
      const hasActiveProgress = data?.initial_pull_progress !== null && data?.initial_pull_progress !== undefined;
      const hasYearsInProgress = data?.years_status &&
        Object.values(data.years_status || {}).includes('in_progress');
      const hasJobButNotCompleted = data?.start_year && !data?.initial_pull_completed;

      return (hasActiveProgress || hasYearsInProgress || hasJobButNotCompleted) ? 5000 : false;
    },
  });
};

export const useUpdateCountyPlatform = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ countyId, ...platformData }) => countiesApi.updatePlatform(countyId, platformData),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['counties'],
        refetchType: 'all'
      });
    },
  });
};
