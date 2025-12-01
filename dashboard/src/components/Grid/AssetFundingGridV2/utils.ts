import { ViewMode, ExchangeRate, AssetGridData } from './types';
import { ContractDetails } from '../../../services/api';

export const formatRate = (rate: number | null): string => {
  if (rate === null || rate === undefined) return '-';
  return `${(rate * 100).toFixed(4)}%`;
};

export const formatValue = (value: number | null, viewMode: ViewMode): string => {
  if (value === null || value === undefined) return '-';
  if (viewMode === 'apr') {
    return `${value.toFixed(2)}%`;
  } else {
    return `${(value * 100).toFixed(4)}%`;
  }
};

export const formatInterval = (hours: number | null | undefined): string => {
  if (!hours) return '-';
  if (hours === 1) return '1h';
  if (hours === 2) return '2h';
  if (hours === 4) return '4h';
  if (hours === 8) return '8h';
  return `${hours}h`;
};

export const getRateColor = (rate: number | null): string => {
  if (rate === null || rate === undefined) return 'text-gray-400';
  if (rate > 0) return 'text-green-600';
  if (rate < 0) return 'text-red-600';
  return 'text-gray-400';
};

export const getRateBgColor = (rate: number | null): string => {
  if (rate === null || rate === undefined) return '';
  if (rate > 0.001) return 'bg-green-50';
  if (rate < -0.001) return 'bg-red-50';
  return '';
};

const colorCache = new Map<number | null, string>();
const COLOR_CACHE_MAX_SIZE = 1000;

export const getRateBgColorCached = (rate: number | null): string => {
  if (colorCache.has(rate)) {
    const cached = colorCache.get(rate)!;
    colorCache.delete(rate);
    colorCache.set(rate, cached);
    return cached;
  }

  const color = calculateBinnedBgColor(rate);

  if (colorCache.size >= COLOR_CACHE_MAX_SIZE) {
    const firstKey = colorCache.keys().next().value;
    colorCache.delete(firstKey);
  }

  colorCache.set(rate, color);
  return color;
};

const calculateBinnedBgColor = (rate: number | null): string => {
  if (rate === null || rate === undefined) return '';
  if (rate >= 0.1) return 'bg-green-500/20';
  if (rate >= 0.05) return 'bg-green-400/15';
  if (rate >= 0.01) return 'bg-green-300/10';
  if (rate > 0) return 'bg-green-200/5';
  if (rate === 0) return '';
  if (rate >= -0.01) return 'bg-red-200/5';
  if (rate >= -0.05) return 'bg-red-300/10';
  if (rate >= -0.1) return 'bg-red-400/15';
  return 'bg-red-500/20';
};

export const calculateProjectedFunding = (
  fundingRate: number,
  fundingIntervalHours: number,
  targetTimeframe: '1h' | '8h' | '1d' | '7d'
): number => {
  const timeframeHours: Record<string, number> = {
    '1h': 1,
    '8h': 8,
    '1d': 24,
    '7d': 168
  };

  const hours = timeframeHours[targetTimeframe];
  const periodsInTimeframe = hours / fundingIntervalHours;
  return fundingRate * periodsInTimeframe;
};

export const getDisplayValue = (
  assetData: AssetGridData | undefined,
  exchange: string,
  viewMode: ViewMode
): number | null => {
  const exchangeData = assetData?.exchanges[exchange];

  if (!exchangeData) return null;

  if (viewMode === 'apr') {
    return exchangeData.apr ?? null;
  } else {
    const fundingRate = exchangeData.funding_rate;
    const fundingInterval = exchangeData.funding_interval_hours ?? 8;

    if (fundingRate === null || fundingRate === undefined) return null;

    return calculateProjectedFunding(fundingRate, fundingInterval, viewMode);
  }
};

export const formatOpenInterest = (contract: ContractDetails): string => {
  const oi = contract.open_interest;
  if (!oi) return '-';

  const exchangesWithUsdOi = ['KuCoin', 'Hyperliquid'];

  if (contract.quote_asset === 'USDT' || contract.quote_asset === 'USDC') {
    let usdValue;

    if (exchangesWithUsdOi.includes(contract.exchange)) {
      usdValue = oi;
    } else {
      usdValue = oi * (contract.mark_price || 0);
    }

    if (usdValue > 1000000000) {
      return `${(usdValue / 1000000000).toFixed(2)}B USD`;
    } else if (usdValue > 1000000) {
      return `${(usdValue / 1000000).toFixed(2)}M USD`;
    } else if (usdValue > 1000) {
      return `${(usdValue / 1000).toFixed(2)}K USD`;
    }
    return `${usdValue.toLocaleString()} USD`;
  }

  if (contract.symbol.includes('USD_PERP')) {
    return `${(oi / 1000000).toFixed(2)}M USD`;
  }

  const baseAsset = contract.base_asset;
  if (oi > 1000000) {
    return `${(oi / 1000000).toFixed(2)}M ${baseAsset}`;
  } else if (oi > 1000) {
    return `${(oi / 1000).toFixed(2)}K ${baseAsset}`;
  }
  return `${oi.toLocaleString()} ${baseAsset}`;
};

export const formatPrice = (price: number): string => {
  if (!price) return '-';
  return `$${price.toLocaleString('en-US', {
    minimumFractionDigits: 5,
    maximumFractionDigits: 5
  })}`;
};

export const isHighlightedZScore = (zScore: number | null | undefined): boolean => {
  if (zScore === null || zScore === undefined) return false;
  return Math.abs(zScore) >= 2;
};

export const isHighlightedPercentile = (percentile: number | null | undefined): boolean => {
  if (percentile === null || percentile === undefined) return false;
  return percentile >= 90 || percentile <= 10;
};

export const getZScoreColor = (zScore: number | null | undefined): string => {
  if (zScore === null || zScore === undefined) return 'text-gray-600';
  if (Math.abs(zScore) >= 2) return 'text-orange-600 font-bold';
  if (Math.abs(zScore) >= 1) return 'text-sky-600';
  return 'text-gray-600';
};

export const getPercentileColor = (percentile: number | null | undefined): string => {
  if (percentile === null || percentile === undefined) return 'text-gray-600';
  if (percentile >= 90 || percentile <= 10) return 'text-orange-600 font-bold';
  if (percentile >= 75 || percentile <= 25) return 'text-sky-600';
  return 'text-gray-600';
};

export const doesContractMatchSearch = (contract: ContractDetails, searchTerm: string): boolean => {
  if (!searchTerm) return false;
  const searchLower = searchTerm.toLowerCase();
  return contract.symbol.toLowerCase().includes(searchLower);
};
