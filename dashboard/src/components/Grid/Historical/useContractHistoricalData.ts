import { useQuery } from '@tanstack/react-query';

export interface HistoricalDataPoint {
  timestamp: string;
  displayTime?: string;
  funding_rate: number | null;
  apr: number | null;
  mark_price?: number | null;
  open_interest?: number | null;
}

export interface ContractStats {
  mark_price?: number;
  funding_rate?: number;
  apr?: number;
  z_score?: number;
  percentile?: number;
  mean_30d?: number;
  std_dev_30d?: number;
  funding_interval_hours?: number;
}

interface ContractHistoricalDataResponse {
  historicalData: HistoricalDataPoint[];
  contractStats: ContractStats | null;
  fundingInterval: number;
  baseAsset: string;
}

interface UseContractHistoricalDataParams {
  exchange: string | undefined;
  symbol: string | undefined;
  enabled?: boolean;
}

async function fetchContractHistoricalData(
  exchange: string,
  symbol: string
): Promise<ContractHistoricalDataResponse> {
  const [statsResponse, historicalResponse] = await Promise.all([
    fetch(
      `http://localhost:8000/api/contracts-with-zscores?exchange=${exchange}&search=${symbol}`
    ),
    fetch(
      `http://localhost:8000/api/historical-funding-by-contract/${exchange}/${symbol}?days=30`
    )
  ]);

  if (!statsResponse.ok || !historicalResponse.ok) {
    throw new Error(`Failed to fetch data for ${exchange}/${symbol}`);
  }

  const [statsResult, historicalResult] = await Promise.all([
    statsResponse.json(),
    historicalResponse.json()
  ]);

  const contractStat = statsResult.contracts?.find(
    (c: any) => c.exchange === exchange && c.contract === symbol
  ) || statsResult.contracts?.[0];

  const contractStats: ContractStats | null = contractStat ? {
    mark_price: contractStat.mark_price,
    funding_rate: contractStat.funding_rate,
    apr: contractStat.apr,
    z_score: contractStat.z_score,
    percentile: contractStat.percentile,
    mean_30d: contractStat.mean_30d,
    std_dev_30d: contractStat.std_dev_30d,
    funding_interval_hours: contractStat.funding_interval_hours || 8
  } : null;

  const processedData = historicalResult.data?.map((item: any) => ({
    timestamp: item.timestamp,
    displayTime: item.timestamp,
    funding_rate: item.funding_rate !== null ? item.funding_rate * 100 : null,
    apr: item.apr || null,
    mark_price: item.mark_price || null,
    open_interest: item.open_interest || null
  })) || [];

  const chronologicalData = processedData.reverse();

  return {
    historicalData: chronologicalData,
    contractStats,
    fundingInterval: historicalResult.funding_interval_hours || 8,
    baseAsset: historicalResult.base_asset || symbol || ''
  };
}

export function useContractHistoricalData({
  exchange,
  symbol,
  enabled = true
}: UseContractHistoricalDataParams) {
  return useQuery({
    queryKey: ['contract-historical', exchange, symbol],
    queryFn: () => {
      if (!exchange || !symbol) {
        throw new Error('Exchange and symbol are required');
      }
      return fetchContractHistoricalData(exchange, symbol);
    },
    enabled: enabled && !!exchange && !!symbol,
    staleTime: 5000,
    refetchInterval: 30000,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000)
  });
}
