import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { permitsApi } from '../api/permits';

export const usePermits = (params = {}) => {
  return useQuery({
    queryKey: ['permits', params],
    queryFn: () => permitsApi.getAll(params),
  });
};

export const usePermit = (id) => {
  return useQuery({
    queryKey: ['permits', id],
    queryFn: () => permitsApi.getById(id),
    enabled: !!id,
  });
};

export const usePullPermits = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ countyId, params }) => permitsApi.pullPermits(countyId, params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['permits'] });
      queryClient.invalidateQueries({ queryKey: ['counties'] });
    },
  });
};
