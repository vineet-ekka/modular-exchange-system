import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from './useDataQueries';
import { fetchContractsByAsset } from '../services/api';

export function useContractPreload(assets: string[], enabled = true) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled || assets.length === 0) return;

    const topAssets = assets.slice(0, 100);

    topAssets.forEach((asset) => {
      queryClient.prefetchQuery({
        queryKey: queryKeys.contractsByAsset(asset),
        queryFn: () => fetchContractsByAsset(asset),
        staleTime: 300000,
      });
    });
  }, [assets, enabled, queryClient]);
}
