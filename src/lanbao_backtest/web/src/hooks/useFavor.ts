import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { favorApi, FavorCondition, PickRequest } from '../api/favor';

const KEY = 'favor';

export function useWatchlist(account_id?: string, group_name?: string) {
  return useQuery({
    queryKey: [KEY, 'watchlist', account_id, group_name],
    queryFn: () => favorApi.getWatchlist(account_id, group_name),
  });
}

export function usePick() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: favorApi.pick,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [KEY, 'watchlist'] });
    },
  });
}

export function useAddToWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: favorApi.addToWatchlist,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [KEY, 'watchlist'] });
    },
  });
}

export function useRemoveFromWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ code, account_id, group_name }: { code: string; account_id?: string; group_name?: string }) =>
      favorApi.removeFromWatchlist(code, account_id, group_name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [KEY, 'watchlist'] });
    },
  });
}

export function useConditions() {
  return useQuery({
    queryKey: [KEY, 'conditions'],
    queryFn: favorApi.listConditions,
  });
}

export function useSaveCondition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: favorApi.saveCondition,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [KEY, 'conditions'] });
    },
  });
}

export function useDeleteCondition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: favorApi.deleteCondition,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [KEY, 'conditions'] });
    },
  });
}
