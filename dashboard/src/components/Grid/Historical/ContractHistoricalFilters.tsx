import React from 'react';
import clsx from 'clsx';

export interface PeriodInfo {
  enabled: boolean;
  completeness: number;
  rawCompleteness: number;
  actualPoints: number;
  expectedPoints: number;
  quality: 'high' | 'medium' | 'low';
  showWarning: boolean;
}

export interface QualityMap {
  [key: number]: PeriodInfo;
}

interface ContractHistoricalFiltersProps {
  timeRange: number;
  onTimeRangeChange: (days: number) => void;
  dataQuality: QualityMap;
  hasMinimumData: boolean;
  periodAverage: number | null;
  lastUpdate: Date;
  onShowPeriodAverageToggle: () => void;
  onRefresh: () => void;
  onExportCSV: () => void;
  showPeriodAverage: boolean;
}

export const ContractHistoricalFilters = React.memo<ContractHistoricalFiltersProps>(({
  timeRange,
  onTimeRangeChange,
  dataQuality,
  hasMinimumData,
  periodAverage,
  lastUpdate,
  onShowPeriodAverageToggle,
  onRefresh,
  onExportCSV,
  showPeriodAverage
}) => {
  const selectedPeriodQuality = dataQuality[timeRange];

  return (
    <>
      <div className="px-6 py-3 border-b border-light-border bg-white">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-2">
            {!hasMinimumData ? (
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-500">📊 Showing all available data</span>
                <span className="text-xs text-gray-400">
                  (Period selection available after 7 days of data)
                </span>
              </div>
            ) : (
              <>
                <span className="text-sm text-gray-600 mr-2">Time Period:</span>
                {[1, 7, 14, 30].map(period => {
                  const periodInfo = dataQuality[period];
                  if (!periodInfo?.enabled) return null;

                  return (
                    <button
                      key={period}
                      onClick={() => onTimeRangeChange(period)}
                      className={clsx(
                        'px-3 py-1 rounded text-sm font-medium transition-colors',
                        timeRange === period
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      )}
                    >
                      {period}D
                      {periodInfo.showWarning && (
                        <span className="ml-1 text-xs text-yellow-600">⚠</span>
                      )}
                    </button>
                  );
                })}
              </>
            )}
          </div>
          <div className="flex items-center space-x-4">
            {periodAverage !== null && (
              <div className="px-3 py-1 bg-orange-50 border border-orange-200 rounded">
                <span className="text-xs text-gray-600 mr-2">Period Average:</span>
                <span className="text-sm font-semibold text-orange-600">
                  {periodAverage.toFixed(4)}%
                </span>
              </div>
            )}
            <div className="text-xs text-gray-500">
              Last updated: {lastUpdate.toLocaleTimeString('en-US', { timeZone: 'UTC', timeZoneName: 'short' })}
            </div>
          </div>
        </div>
      </div>

      {selectedPeriodQuality && (
        <div className="px-6 py-3 border-b border-light-border bg-gray-50 flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <div className="text-xs text-gray-600" title={
              selectedPeriodQuality.rawCompleteness > 100
                ? `Actual: ${selectedPeriodQuality.actualPoints} points | Expected: ${selectedPeriodQuality.expectedPoints} points | Raw completeness: ${selectedPeriodQuality.rawCompleteness.toFixed(1)}%`
                : `Actual: ${selectedPeriodQuality.actualPoints} points | Expected: ${selectedPeriodQuality.expectedPoints} points`
            }>
              Data Completeness: {selectedPeriodQuality.completeness.toFixed(1)}%
              {selectedPeriodQuality.rawCompleteness > 100 && (
                <span className="ml-1 text-blue-600" title="More data points than expected - excellent coverage!">📊</span>
              )}
              <span className={clsx(
                'ml-2 px-2 py-0.5 rounded text-xs',
                selectedPeriodQuality.rawCompleteness > 100 ? 'bg-blue-100 text-blue-700' :
                selectedPeriodQuality.quality === 'high' ? 'bg-green-100 text-green-700' :
                selectedPeriodQuality.quality === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                'bg-orange-100 text-orange-700'
              )}>
                {selectedPeriodQuality.rawCompleteness > 100 ? 'EXCELLENT' : selectedPeriodQuality.quality.toUpperCase()}
              </span>
            </div>
          </div>

          <div className="flex space-x-2">
            <button
              onClick={onShowPeriodAverageToggle}
              className={clsx(
                'px-3 py-1 rounded text-sm font-medium transition-colors border',
                showPeriodAverage
                  ? 'bg-orange-500 text-white border-orange-500 hover:bg-orange-600'
                  : 'bg-white text-text-secondary border-light-border hover:bg-gray-100'
              )}
            >
              {showPeriodAverage ? 'Hide' : 'Show'} Period Avg
            </button>
            <button
              onClick={onRefresh}
              className="px-3 py-1 bg-white text-text-secondary hover:bg-gray-100 border border-light-border rounded text-sm"
            >
              Refresh
            </button>
            <button
              onClick={onExportCSV}
              className="px-3 py-1 bg-accent-green text-white hover:bg-green-600 rounded text-sm shadow-sm"
            >
              Export CSV
            </button>
          </div>
        </div>
      )}
    </>
  );
}, (prevProps, nextProps) => {
  return (
    prevProps.timeRange === nextProps.timeRange &&
    prevProps.dataQuality === nextProps.dataQuality &&
    prevProps.hasMinimumData === nextProps.hasMinimumData &&
    prevProps.periodAverage === nextProps.periodAverage &&
    prevProps.showPeriodAverage === nextProps.showPeriodAverage &&
    prevProps.lastUpdate.getTime() === nextProps.lastUpdate.getTime()
  );
});

ContractHistoricalFilters.displayName = 'ContractHistoricalFilters';
