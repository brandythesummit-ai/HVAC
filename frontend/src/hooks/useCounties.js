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
      queryClient.invalidateQueries({ queryKey: ['counties'] });
    },
  });
};

export const useUpdateCounty = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => countiesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['counties'] });
    },
  });
};

export const useDeleteCounty = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: countiesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['counties'] });
    },
  });
};

export const useTestCountyConnection = () => {
  return useMutation({
    mutationFn: countiesApi.testConnection,
  });
};
