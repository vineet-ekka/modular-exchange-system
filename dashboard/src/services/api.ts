import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
});

export interface FundingRate {
  exchange: string;
  symbol: string;
  base_asset: string;
  quote_asset: string;
  funding_rate: number;
  funding_interval_hours: number;
  apr: number;
  index_price: number;
  mark_price: number;
  open_interest: number;
  contract_type: string;
  market_type: string;
  last_updated: string;
}

export interface Statistics {
  total_contracts: number;
  avg_apr: number;
  highest_apr: number;
  lowest_apr: number;
  active_exchanges: number;
  unique_assets: number;
  total_open_interest: number;
  highest_symbol?: string;
  highest_exchange?: string;
  lowest_symbol?: string;
  lowest_exchange?: string;
}

export interface Filters {
  exchange?: string;
  baseAsset?: string;
  minAPR?: number;
  maxAPR?: number;
}

export const fetchFundingRates = async (filters: Filters = {}): Promise<FundingRate[]> => {
  try {
    const params = new URLSearchParams();
    // Fetch all contracts (max 2000)
    params.append('limit', '2000');
    if (filters.exchange) params.append('exchange', filters.exchange);
    if (filters.baseAsset) params.append('base_asset', filters.baseAsset);
    if (filters.minAPR !== undefined) params.append('min_apr', filters.minAPR.toString());
    if (filters.maxAPR !== undefined) params.append('max_apr', filters.maxAPR.toString());
    
    const response = await api.get(`/api/funding-rates?${params}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching funding rates:', error);
    return [];
  }
};

export const fetchStatistics = async (): Promise<Statistics | null> => {
  try {
    const response = await api.get('/api/statistics');
    return response.data;
  } catch (error) {
    console.error('Error fetching statistics:', error);
    return null;
  }
};

export const fetchTopAPR = async (limit: number = 20): Promise<FundingRate[]> => {
  try {
    const response = await api.get(`/api/top-apr/${limit}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching top APR:', error);
    return [];
  }
};

export const fetchGroupByAsset = async () => {
  try {
    const response = await api.get('/api/group-by-asset');
    return response.data;
  } catch (error) {
    console.error('Error fetching grouped data:', error);
    return [];
  }
};

export const fetchHistorical = async (symbol: string, days: number = 7) => {
  try {
    const response = await api.get(`/api/historical/${symbol}?days=${days}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching historical data:', error);
    return null;
  }
};

export const fetchExchanges = async (): Promise<string[]> => {
  try {
    const response = await api.get('/api/exchanges');
    return response.data;
  } catch (error) {
    console.error('Error fetching exchanges:', error);
    return [];
  }
};

export const fetchAssets = async (): Promise<string[]> => {
  try {
    const response = await api.get('/api/assets');
    return response.data;
  } catch (error) {
    console.error('Error fetching assets:', error);
    return [];
  }
};

export interface HistoricalFundingData {
  symbol: string;
  exchange: string;
  data_points: number;
  start_time: string;
  end_time: string;
  data: Array<{
    exchange: string;
    symbol: string;
    funding_rate: number;
    funding_time: string;
    mark_price: number;
    funding_interval_hours: number;
  }>;
}

export interface SparklineData {
  symbol: string;
  exchange: string;
  hours: number;
  data_points: number;
  sparkline: Array<{
    time: string;
    value: number;
    min: number;
    max: number;
    count: number;
  }>;
}

export const fetchHistoricalFunding = async (
  symbol: string,
  startTime?: string,
  endTime?: string,
  exchange: string = 'Binance'
): Promise<HistoricalFundingData | null> => {
  try {
    const params = new URLSearchParams();
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);
    params.append('exchange', exchange);
    
    const response = await api.get(`/api/historical-funding/${symbol}?${params}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching historical funding:', error);
    return null;
  }
};

export const fetchFundingSparkline = async (
  symbol: string,
  hours: number = 48,
  exchange: string = 'Binance'
): Promise<SparklineData | null> => {
  try {
    const params = new URLSearchParams();
    params.append('hours', hours.toString());
    params.append('exchange', exchange);
    
    const response = await api.get(`/api/funding-sparkline/${symbol}?${params}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching sparkline data:', error);
    return null;
  }
};

// Phase 6 API - Current Funding
export interface CurrentFundingData {
  asset: string;
  symbol: string;
  exchange: string;
  funding_rate: number;
  apr: number;
  funding_interval_hours: number;
  next_funding_time: string;
  time_until_funding: {
    hours: number;
    minutes: number;
    seconds: number;
    display: string;
  };
  last_updated: string;
  error?: string;
}

export const fetchCurrentFunding = async (
  asset: string
): Promise<CurrentFundingData | null> => {
  try {
    const response = await api.get(`/api/current-funding/${asset}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching current funding:', error);
    return null;
  }
};

// Asset Grid API
export interface AssetGridData {
  asset: string;
  exchanges: Record<string, {
    funding_rate: number | null;
    apr: number | null;
  }>;
}

export interface AssetGridResponse {
  data: AssetGridData[];
  total_assets: number;
  timestamp: string;
}

// Contract Details Interface for expanded view
export interface ContractDetails {
  symbol: string;           // Contract Name
  exchange: string;         // Exchange Name
  base_asset: string;       // Base Asset
  quote_asset: string;      // Quote Asset
  funding_rate: number;     // Funding Rate
  apr: number;             // APR
  open_interest: number;    // Open Interest
  mark_price: number;       // Mark Price
  index_price: number;      // Index Price
  funding_interval_hours: number;
  contract_type: string;
  market_type: string;
  last_updated: string;
}

export const fetchFundingRatesGrid = async (): Promise<AssetGridResponse | null> => {
  try {
    const response = await api.get('/api/funding-rates-grid');
    return response.data;
  } catch (error) {
    console.error('Error fetching funding rates grid:', error);
    return null;
  }
};

// Historical by Asset API
export interface HistoricalByAssetResponse {
  asset: string;
  exchanges: string[];
  days: number;
  data_points: number;
  data: Array<{
    timestamp: string;
    [exchange: string]: string | number | null;
  }>;
}

export const fetchHistoricalFundingByAsset = async (
  asset: string,
  days: number = 7
): Promise<HistoricalByAssetResponse | null> => {
  try {
    const response = await api.get(`/api/historical-funding-by-asset/${asset}?days=${days}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching historical funding by asset:', error);
    return null;
  }
};

// Fetch contracts by asset for expanded view
export const fetchContractsByAsset = async (asset: string): Promise<ContractDetails[]> => {
  try {
    console.log(`API: Fetching contracts for asset: ${asset}`);
    const response = await api.get(`/api/funding-rates?base_asset=${asset}&limit=100`);
    console.log(`API: Response for ${asset}:`, response.data);
    
    // Ensure we return an array
    if (Array.isArray(response.data)) {
      return response.data;
    } else if (response.data && response.data.data) {
      // Handle if API returns wrapped response
      return response.data.data;
    } else {
      console.warn(`API: Unexpected response format for ${asset}:`, response.data);
      return [];
    }
  } catch (error) {
    console.error('Error fetching contracts for asset:', error);
    return [];
  }
};