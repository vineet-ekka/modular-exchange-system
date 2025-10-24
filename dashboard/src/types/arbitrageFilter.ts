/**
 * Type definitions for the Arbitrage Filter System
 */

export interface Asset {
  symbol: string;
  name: string;
  exchanges: number;
  avg_spread_pct: number;
  avg_apr: number;
  max_spread_pct: number;
  total_opportunities: number;
  last_updated?: string;
}

export interface ArbitrageFilterState {
  selectedAssets: Asset[];
  selectedExchanges: Set<string>;
  selectedIntervals: Set<number>;
  minApr: number | null;
  maxApr: number | null;
  minOIEither: number | null;
  minOICombined: number | null;
}

export const DEFAULT_ARBITRAGE_FILTER_STATE: ArbitrageFilterState = {
  selectedAssets: [],
  selectedExchanges: new Set(),
  selectedIntervals: new Set(),
  minApr: null,
  maxApr: null,
  minOIEither: null,
  minOICombined: null,
};

export interface AssetSearchResponse {
  results: Asset[];
  query: string;
  count: number;
  timestamp: string;
}

export interface FilterChangeHandler {
  (state: Partial<ArbitrageFilterState>): void;
}