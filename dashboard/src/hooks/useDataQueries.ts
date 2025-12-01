import { useQuery, UseQueryResult } from '@tanstack/react-query';
import {
  fetchFundingRatesGrid,
  fetchStatistics,
  fetchContractsByAsset,
  AssetGridResponse,
  Statistics,
  ContractDetails,
} from '../services/api';
import {
  fetchContractArbitrageOpportunities,
  ContractArbitrageResponse,
} from '../services/arbitrage';

export interface ArbitrageQueryFilters {
  minSpread?: number;
  page?: number;
  pageSize?: number;
  filters?: {
    selectedExchanges?: string[];
    selectedAssets?: string[];
    minAPR?: number;
    maxAPR?: number;
    intervals?: string[];
  };
}

export const queryKeys = {
  gridData: ['funding-rates-grid'] as const,
  dashboardStats: ['dashboard-stats'] as const,
  arbitrageOpportunities: (params?: ArbitrageQueryFilters) =>
    ['arbitrage-opportunities', params] as const,
  contractsByAsset: (asset: string) =>
    ['contracts-by-asset', asset] as const,
};

export function useGridData(): UseQueryResult<AssetGridResponse | null, Error> {
  return useQuery({
    queryKey: queryKeys.gridData,
    queryFn: fetchFundingRatesGrid,
    staleTime: 25000,
    refetchInterval: 30000,
  });
}

export function useDashboardStats(): UseQueryResult<Statistics | null, Error> {
  return useQuery({
    queryKey: queryKeys.dashboardStats,
    queryFn: fetchStatistics,
    staleTime: 25000,
    refetchInterval: 30000,
  });
}

export function useArbitrageOpportunities(
  minSpread = 0.0001,
  page = 1,
  pageSize = 20,
  filters: ArbitrageQueryFilters['filters'] = {}
): UseQueryResult<ContractArbitrageResponse, Error> {
  const filterKey = JSON.stringify(filters);
  return useQuery({
    queryKey: ['arbitrage-opportunities', minSpread, page, pageSize, filterKey],
    queryFn: () => fetchContractArbitrageOpportunities(minSpread, page, pageSize, filters),
    staleTime: 25000,
    refetchInterval: 30000,
    enabled: true,
    placeholderData: undefined,
  });
}

export function useContractsByAsset(
  asset: string,
  enabled = false
): UseQueryResult<ContractDetails[], Error> {
  return useQuery({
    queryKey: queryKeys.contractsByAsset(asset),
    queryFn: () => fetchContractsByAsset(asset),
    staleTime: 60000,
    gcTime: 300000,
    enabled,
  });
}
