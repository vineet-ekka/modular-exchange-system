/**
 * Type definitions for funding chart data structures
 */

export interface FundingDataPoint {
  timestamp: string;
  rawTimestamp?: string;
  displayTime?: string;
  [key: string]: string | number | boolean | null | undefined;
}

export interface ProcessedFundingData extends FundingDataPoint {
  [contractName: `${string}_isActual`]: boolean;
  [contractName: `${string}_change`]: number | null;
  [contractName: `${string}_interval`]: number;
  [contractName: `${string}_apr`]: number | null;
}

export type FundingInterval = 1 | 2 | 4 | 8;

export interface ContractInfo {
  symbol: string;
  exchange: string;
  fundingInterval?: FundingInterval;
}

export interface FundingStatistics {
  avg: number;
  min: number;
  max: number;
  count: number;
}

export interface ChartConfiguration {
  showReferenceLines: boolean;
  animationEnabled: boolean;
  stepFunction: boolean;
  showTooltip: boolean;
}

export const DEFAULT_CHART_CONFIG: ChartConfiguration = {
  showReferenceLines: true,
  animationEnabled: false,
  stepFunction: true,
  showTooltip: true
};