import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { backtestApi } from '../api/backtest';
import { useBacktestStore } from '../stores/backtestStore';

const KEY = 'backtests';

export function useBacktestList() {
  const { filters, page, limit } = useBacktestStore();
  return useQuery({
    queryKey: [KEY, 'list', filters, page, limit],
    queryFn: () => backtestApi.list(filters, page, limit),
    staleTime: 30000,
  });
}

export function useBacktestDetail(id: string | undefined) {
  return useQuery({
    queryKey: [KEY, 'detail', id],
    queryFn: () => backtestApi.get(id!),
    enabled: !!id,
  });
}

export function useEquityCurve(id: string | undefined) {
  return useQuery({
    queryKey: [KEY, 'equity', id],
    queryFn: () => backtestApi.getEquity(id!),
    enabled: !!id,
  });
}

export function useTrades(id: string | undefined) {
  return useQuery({
    queryKey: [KEY, 'trades', id],
    queryFn: () => backtestApi.getTrades(id!),
    enabled: !!id,
  });
}

export function useMonthlyReturns(id: string | undefined) {
  return useQuery({
    queryKey: [KEY, 'monthly', id],
    queryFn: () => backtestApi.getMonthly(id!),
    enabled: !!id,
  });
}

export function useDeleteBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: backtestApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, 'list'] }),
  });
}

export function useRunBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: backtestApi.run,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, 'list'] }),
  });
}
