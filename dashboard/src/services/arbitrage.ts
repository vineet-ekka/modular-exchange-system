import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface ArbitrageOpportunity {
  asset: string;
  long_exchange: string;
  short_exchange: string;
  long_rate: number;
  short_rate: number;
  long_apr: number;
  short_apr: number;
  long_interval_hours: number;
  short_interval_hours: number;
  rate_spread: number;
  rate_spread_pct: number;
  apr_spread: number;
  // Statistical fields
  long_zscore?: number;
  short_zscore?: number;
  spread_zscore?: number;
  percentile?: number;
  is_significant?: boolean;
  significance_score?: number;
  data_points?: number;
}

export interface ArbitrageResponse {
  opportunities: ArbitrageOpportunity[];
  statistics: {
    total_opportunities: number;
    average_spread: number;
    max_spread: number;
    max_apr_spread: number;
    most_common_long_exchange: string | null;
    most_common_short_exchange: string | null;
    // New statistical fields
    significant_count?: number;
    extreme_count?: number;
    avg_significance_score?: number;
    with_statistics?: number;
  };
  parameters: {
    min_spread: number;
    top_n: number;
  };
  timestamp: string;
}

export const fetchArbitrageOpportunities = async (
  minSpread = 0.0001,
  topN = 20
): Promise<ArbitrageResponse> => {
  try {
    const response = await axios.get<ArbitrageResponse>(
      `${API_URL}/api/arbitrage/opportunities`,
      {
        params: {
          min_spread: minSpread,
          top_n: topN,
        },
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching arbitrage opportunities:', error);
    throw error;
  }
};

// V2 Contract-Level Interfaces
export interface ContractArbitrageOpportunity {
  asset: string;
  // Long contract details
  long_contract: string;
  long_exchange: string;
  long_rate: number;
  long_apr: number | null;
  long_interval_hours: number;
  long_zscore: number | null;
  long_percentile: number | null;
  long_open_interest: number | null;
  // Short contract details
  short_contract: string;
  short_exchange: string;
  short_rate: number;
  short_apr: number | null;
  short_interval_hours: number;
  short_zscore: number | null;
  short_percentile: number | null;
  short_open_interest: number | null;
  // Spreads
  rate_spread: number;
  rate_spread_pct: number;
  apr_spread: number | null;
  // Spread Z-score statistics
  spread_zscore: number | null;
  spread_mean: number | null;
  spread_std_dev: number | null;
  // New practical metrics
  long_hourly_rate: number;
  short_hourly_rate: number;
  effective_hourly_spread: number;
  sync_period_hours: number;
  long_sync_funding: number;
  short_sync_funding: number;
  sync_period_spread: number;
  long_daily_funding: number;
  short_daily_funding: number;
  daily_spread: number;
  // Periodic funding spreads
  weekly_spread: number;
  monthly_spread: number;
  quarterly_spread: number;
  yearly_spread: number;
  // Combined metrics
  combined_open_interest?: number;
  is_significant: boolean;
}

export interface ContractArbitrageResponse {
  opportunities: ContractArbitrageOpportunity[];
  statistics: {
    total_opportunities: number;
    average_spread: number;
    max_spread: number;
    max_apr_spread: number;
    max_daily_spread?: number;
    max_hourly_spread?: number;
    significant_count: number;
    contracts_analyzed: number;
  };
  pagination?: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
  parameters: {
    min_spread: number;
    page?: number;
    page_size?: number;
    top_n?: number;  // Keep for backward compatibility
  };
  timestamp: string;
  version: string;
}

export interface OpportunityDetailResponse {
  opportunity: {
    asset: string;
    long_exchange: string;
    long_contract: string;
    long_rate: number;
    long_open_interest: number | null;
    long_interval_hours: number;
    long_zscore: number | null;
    short_exchange: string;
    short_contract: string;
    short_rate: number;
    short_open_interest: number | null;
    short_interval_hours: number;
    short_zscore: number | null;
    rate_spread: number;
    rate_spread_pct: number;
    apr_spread: number;
    daily_spread: number;
    effective_hourly_spread: number;
  };
  historical: {
    daily_data: Array<{
      date: string;
      avg_apr_spread: number;
      max_apr_spread: number;
      min_apr_spread: number;
      data_points: number;
    }>;
    statistics: {
      avg_30d_spread: number | null;
      max_30d_spread: number | null;
      min_30d_spread: number | null;
      data_days: number;
    };
  };
  timestamp: string;
}

export const fetchOpportunityDetail = async (
  asset: string,
  longExchange: string,
  shortExchange: string
): Promise<OpportunityDetailResponse> => {
  const response = await axios.get<OpportunityDetailResponse>(
    `${API_URL}/api/arbitrage/opportunity-detail/${encodeURIComponent(asset)}/${encodeURIComponent(longExchange)}/${encodeURIComponent(shortExchange)}`
  );
  return response.data;
};

export const fetchContractArbitrageOpportunities = async (
  minSpread = 0.0001,
  page = 1,
  pageSize = 20,
  filters: Record<string, any> = {}
): Promise<ContractArbitrageResponse> => {
  try {
    // Build query parameters
    const params = new URLSearchParams({
      min_spread: minSpread.toString(),
      page: page.toString(),
      page_size: pageSize.toString(),
    });

    // Add array filters (assets, exchanges, intervals)
    if (filters.assets && filters.assets.length > 0) {
      filters.assets.forEach((asset: string) => params.append('assets', asset));
    }

    if (filters.exchanges && filters.exchanges.length > 0) {
      filters.exchanges.forEach((exchange: string) => params.append('exchanges', exchange));
    }

    if (filters.intervals && filters.intervals.length > 0) {
      filters.intervals.forEach((interval: number) => params.append('intervals', interval.toString()));
    }

    // Add scalar filters
    if (filters.min_apr !== undefined && filters.min_apr !== null) {
      params.append('min_apr', filters.min_apr.toString());
    }

    if (filters.max_apr !== undefined && filters.max_apr !== null) {
      params.append('max_apr', filters.max_apr.toString());
    }

    if (filters.min_oi_either !== undefined && filters.min_oi_either !== null) {
      params.append('min_oi_either', filters.min_oi_either.toString());
    }

    if (filters.min_oi_combined !== undefined && filters.min_oi_combined !== null) {
      params.append('min_oi_combined', filters.min_oi_combined.toString());
    }

    if (filters.sort_by) {
      params.append('sort_by', filters.sort_by);
    }

    if (filters.sort_dir) {
      params.append('sort_dir', filters.sort_dir);
    }

    const response = await axios.get<ContractArbitrageResponse>(
      `${API_URL}/api/arbitrage/opportunities-v2?${params.toString()}`
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching contract-level arbitrage opportunities:', error);
    throw error;
  }
};