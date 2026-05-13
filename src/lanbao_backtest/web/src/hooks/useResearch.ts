import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { researchApi } from '../api/research';

const KEY = 'research';

export function useTriggerMarketDaily() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: researchApi.triggerMarketDaily,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [KEY, 'reports'] });
    },
  });
}

export function useTriggerStockResearch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: researchApi.triggerStockResearch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [KEY, 'reports'] });
    },
  });
}

export function useResearchStatus(reportId: string | null) {
  return useQuery({
    queryKey: [KEY, 'status', reportId],
    queryFn: () => researchApi.getStatus(reportId!),
    enabled: !!reportId,
    refetchInterval: (query) =>
      query.state.data?.status === 'running' ? 3000 : false,
  });
}

export function useResearchReport(reportId: string | null) {
  return useQuery({
    queryKey: [KEY, 'report', reportId],
    queryFn: () => researchApi.getReport(reportId!),
    enabled: !!reportId,
  });
}

export function useResearchReports(
  params?: { report_type?: string; limit?: number; offset?: number },
) {
  return useQuery({
    queryKey: [KEY, 'reports', params],
    queryFn: () => researchApi.listReports(params),
  });
}
