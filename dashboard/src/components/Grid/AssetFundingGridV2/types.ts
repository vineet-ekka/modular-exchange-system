import { ContractDetails } from '../../../services/api';

export interface ExchangeRate {
  funding_rate: number | null;
  apr: number | null;
  funding_interval_hours?: number | null;
}

export interface AssetGridData {
  asset: string;
  exchanges: Record<string, ExchangeRate>;
}

export type ViewMode = 'apr' | '1h' | '8h' | '1d' | '7d';

export interface GridState {
  loading: boolean;
  searchTerm: string;
  expandedAssets: Set<string>;
  contractsData: Record<string, ContractDetails[]>;
  loadingContracts: Set<string>;
  autoExpandedAssets: Set<string>;
  viewMode: ViewMode;
}

export interface ContractsCache {
  [asset: string]: ContractDetails[];
}

export interface ViewModeOption {
  value: ViewMode;
  label: string;
  title: string;
}
