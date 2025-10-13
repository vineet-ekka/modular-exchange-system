export interface ExchangeMetadata {
  type: 'CEX' | 'DEX';
  category: 'Major' | 'Emerging' | 'Options';
  contracts: number;
  color: string;
  funding_intervals: number[] | 'variable';
  orderPriority: number;
  disabled?: boolean;
}

export interface ExchangeFilterState {
  selectedExchanges: Set<string>;
  filterExpanded: boolean;
  hideEmptyAssets: boolean;
  showOnlyCrossListed: boolean;
  highlightMissing: boolean;
}

export interface PresetDefinition {
  id: string;
  label: string;
  exchanges: string[];
  count: number;
}

export interface AssetGridData {
  asset: string;
  exchanges: Record<string, {
    funding_rate: number | null;
    apr: number | null;
    funding_interval_hours?: number | null;
  }>;
}
