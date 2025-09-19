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
    significant_count: number;
    contracts_analyzed: number;
  };
  parameters: {
    min_spread: number;
    top_n: number;
  };
  timestamp: string;
  version: string;
}

export const fetchContractArbitrageOpportunities = async (
  minSpread = 0.0001,
  topN = 20
): Promise<ContractArbitrageResponse> => {
  try {
    const response = await axios.get<ContractArbitrageResponse>(
      `${API_URL}/api/arbitrage/opportunities-v2`,
      {
        params: {
          min_spread: minSpread,
          top_n: topN,
        },
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching contract-level arbitrage opportunities:', error);
    throw error;
  }
};