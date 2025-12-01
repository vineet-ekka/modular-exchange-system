import React from 'react';
import { ContractStats } from './useContractHistoricalData';

interface ContractHistoricalMetricsProps {
  symbol: string | undefined;
  fundingInterval: number;
  contractStats: ContractStats | null;
  periodZScore: number | null;
  periodPercentile: number | null;
  timeRange: number;
  showAllData: boolean;
}

const formatOrdinal = (value: number): string => {
  const suffix = Math.floor(value % 10) === 1 && Math.floor(value) !== 11 ? 'st' :
                 Math.floor(value % 10) === 2 && Math.floor(value) !== 12 ? 'nd' :
                 Math.floor(value % 10) === 3 && Math.floor(value) !== 13 ? 'rd' : 'th';
  return `${Math.floor(value)}${suffix}`;
};

export const ContractHistoricalMetrics = React.memo<ContractHistoricalMetricsProps>(({
  symbol,
  fundingInterval,
  contractStats,
  periodZScore,
  periodPercentile,
  timeRange,
  showAllData
}) => {
  return (
    <div className="px-6 py-4 border-b border-light-border bg-gray-50">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-4">
        <div className="metric-item" data-metric="contract">
          <div className="text-xs sm:text-sm text-gray-500 mb-1">Contract</div>
          <div className="text-base sm:text-lg font-semibold">
            {symbol || '--'}
          </div>
        </div>

        <div className="metric-item" data-metric="interval">
          <div className="text-xs sm:text-sm text-gray-500 mb-1">Interval</div>
          <div className="text-base sm:text-lg font-semibold">
            {fundingInterval ? `${fundingInterval}h` : '--'}
          </div>
        </div>

        <div className="metric-item" data-metric="mark-price">
          <div className="text-xs sm:text-sm text-gray-500 mb-1">Mark Price</div>
          <div className="text-base sm:text-lg font-semibold">
            {contractStats?.mark_price
              ? `$${contractStats.mark_price.toLocaleString(undefined, { minimumFractionDigits: 5, maximumFractionDigits: 5 })}`
              : '--'}
          </div>
        </div>

        <div className="metric-item" data-metric="current-rate">
          <div className="text-xs sm:text-sm text-gray-500 mb-1">Current Rate</div>
          <div className="text-base sm:text-lg font-semibold">
            {contractStats?.funding_rate !== undefined
              ? `${(contractStats.funding_rate * 100).toFixed(4)}%`
              : '--'}
          </div>
        </div>

        <div className="metric-item" data-metric="apr">
          <div className="text-xs sm:text-sm text-gray-500 mb-1">APR</div>
          <div className="text-base sm:text-lg font-semibold">
            {contractStats?.apr !== undefined
              ? `${contractStats.apr.toFixed(4)}%`
              : '--'}
          </div>
        </div>

        <div className="metric-item" data-metric="mean-30d">
          <div className="text-xs sm:text-sm text-gray-500 mb-1">Mean (30d)</div>
          <div className="text-base sm:text-lg font-semibold">
            {contractStats?.mean_30d !== undefined
              ? `${(contractStats.mean_30d * 100).toFixed(4)}%`
              : '--'}
          </div>
        </div>

        <div className="metric-item" data-metric="z-score-period">
          <div className="text-xs sm:text-sm text-gray-500 mb-1">
            Z-Score {showAllData ? '(All)' : `(${timeRange}d)`}
          </div>
          <div className="text-base sm:text-lg font-semibold">
            {periodZScore !== null
              ? periodZScore.toFixed(2)
              : '--'}
          </div>
        </div>

        <div className="metric-item" data-metric="percentile-period">
          <div className="text-xs sm:text-sm text-gray-500 mb-1">
            Percentile {showAllData ? '(All)' : `(${timeRange}d)`}
          </div>
          <div className="text-base sm:text-lg font-semibold">
            {periodPercentile !== null
              ? formatOrdinal(periodPercentile)
              : '--'}
          </div>
        </div>

        <div className="metric-item" data-metric="std-dev-30d">
          <div className="text-xs sm:text-sm text-gray-500 mb-1">Std Dev (30d)</div>
          <div className="text-base sm:text-lg font-semibold">
            {contractStats?.std_dev_30d !== undefined
              ? `${(contractStats.std_dev_30d * 100).toFixed(4)}%`
              : '--'}
          </div>
        </div>
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  return (
    prevProps.symbol === nextProps.symbol &&
    prevProps.fundingInterval === nextProps.fundingInterval &&
    prevProps.contractStats === nextProps.contractStats &&
    prevProps.periodZScore === nextProps.periodZScore &&
    prevProps.periodPercentile === nextProps.periodPercentile &&
    prevProps.timeRange === nextProps.timeRange &&
    prevProps.showAllData === nextProps.showAllData
  );
});

ContractHistoricalMetrics.displayName = 'ContractHistoricalMetrics';
