import React, { useState, useEffect, useCallback, useMemo } from 'react';
import clsx from 'clsx';
import {
  useContractHistoricalData,
  HistoricalDataPoint,
  ContractStats
} from './Historical/useContractHistoricalData';
import { ContractHistoricalChart } from './Historical/ContractHistoricalChart';
import { ContractHistoricalTable } from './Historical/ContractHistoricalTable';
import {
  ContractHistoricalFilters,
  PeriodInfo,
  QualityMap
} from './Historical/ContractHistoricalFilters';
import { ContractHistoricalMetrics } from './Historical/ContractHistoricalMetrics';

class DataQualityValidator {
  static validatePeriodAvailability(
    completeness: number,
    maxGap: number,
    period: number,
    fundingInterval: number
  ): boolean {
    const gapLimits: { [key: number]: number } = {
      1: fundingInterval * 4,
      7: 48,
      14: 72,
      30: 96
    };
    return completeness >= 20 && maxGap <= gapLimits[period];
  }
}

interface HistoricalFundingViewProps {
  asset?: string;
  exchange?: string;
  symbol?: string;
  isContractView?: boolean;
  onUpdate?: () => void;
}

const HistoricalFundingViewContract: React.FC<HistoricalFundingViewProps> = ({
  asset,
  exchange,
  symbol,
  isContractView = false,
  onUpdate
}) => {
  const [timeRange, setTimeRange] = useState(7);
  const [availablePeriods, setAvailablePeriods] = useState<number[]>([]);
  const [dataQuality, setDataQuality] = useState<QualityMap>({});
  const [periodZScore, setPeriodZScore] = useState<number | null>(null);
  const [periodPercentile, setPeriodPercentile] = useState<number | null>(null);
  const [hasMinimumData, setHasMinimumData] = useState<boolean>(true);
  const [showAllData, setShowAllData] = useState<boolean>(false);
  const [showPeriodAverage, setShowPeriodAverage] = useState<boolean>(true);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 25;

  const { data, isLoading, error, refetch } = useContractHistoricalData({
    exchange,
    symbol,
    enabled: isContractView
  });

  const historicalData = data?.historicalData || [];
  const contractStats = data?.contractStats || null;
  const fundingInterval = data?.fundingInterval || 8;
  const baseAsset = data?.baseAsset || '';

  const assessPeriodAvailability = useCallback((
    dataPoints: HistoricalDataPoint[],
    fundingIntervalHours: number
  ): QualityMap => {
    const periods = [1, 7, 14, 30];
    const availability: QualityMap = {};
    const now = new Date();

    periods.forEach(days => {
      const expectedPoints = (days * 24) / fundingIntervalHours;
      const cutoffTime = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
      const periodData = dataPoints.filter(d => new Date(d.timestamp) >= cutoffTime);
      const actualPoints = periodData.filter(d => d.funding_rate !== null).length;
      const rawCompleteness = expectedPoints > 0 ? (actualPoints / expectedPoints) * 100 : 0;
      const completeness = Math.min(rawCompleteness, 100);

      let maxGap = 0;
      for (let i = 1; i < periodData.length; i++) {
        if (periodData[i - 1].timestamp && periodData[i].timestamp) {
          const gap = new Date(periodData[i - 1].timestamp).getTime() -
            new Date(periodData[i].timestamp).getTime();
          maxGap = Math.max(maxGap, gap / (60 * 60 * 1000));
        }
      }

      availability[days] = {
        enabled: DataQualityValidator.validatePeriodAvailability(
          completeness,
          maxGap,
          days,
          fundingIntervalHours
        ),
        completeness,
        rawCompleteness,
        actualPoints,
        expectedPoints,
        quality: completeness >= 90 ? 'high' : completeness >= 70 ? 'medium' : 'low',
        showWarning: completeness >= 50 && completeness < 70
      };
    });

    return availability;
  }, []);

  const calculatePeriodStats = useCallback((
    dataPoints: HistoricalDataPoint[],
    periodDays: number
  ) => {
    const now = new Date();
    const cutoffTime = new Date(now.getTime() - periodDays * 24 * 60 * 60 * 1000);
    const periodData = dataPoints
      .filter(d => new Date(d.timestamp) >= cutoffTime)
      .filter(d => d.funding_rate !== null)
      .map(d => d.funding_rate as number);

    if (periodData.length < 3) return { zScore: null, percentile: null };

    const mean = periodData.reduce((a, b) => a + b, 0) / periodData.length;
    const variance = periodData.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / periodData.length;
    const stdDev = Math.sqrt(variance);

    const currentRate = dataPoints.length > 0 && dataPoints[dataPoints.length - 1].funding_rate !== null
      ? dataPoints[dataPoints.length - 1].funding_rate
      : null;

    if (currentRate === null || stdDev === 0) return { zScore: null, percentile: null };

    const zScore = (currentRate - mean) / stdDev;
    const sortedData = [...periodData].sort((a, b) => a - b);
    const rank = sortedData.filter(v => v <= currentRate).length;
    const percentile = (rank / sortedData.length) * 100;

    return { zScore, percentile };
  }, []);

  useEffect(() => {
    if (historicalData.length > 0) {
      const validDataPoints = historicalData.filter(d => d.funding_rate !== null).length;
      const expectedPointsFor7Days = (7 * 24) / fundingInterval;

      let dataSpanDays = 0;
      if (historicalData.length > 0) {
        const earliestDate = new Date(historicalData[0].timestamp);
        const latestDate = new Date(historicalData[historicalData.length - 1].timestamp);
        dataSpanDays = (latestDate.getTime() - earliestDate.getTime()) / (24 * 60 * 60 * 1000);
      }

      const hasEnoughData = dataSpanDays >= 7 || validDataPoints >= expectedPointsFor7Days * 0.5;
      setHasMinimumData(hasEnoughData);
      setShowAllData(!hasEnoughData);

      if (!hasEnoughData) {
        setAvailablePeriods([]);
      } else {
        const quality = assessPeriodAvailability(historicalData, fundingInterval);
        setDataQuality(quality);

        const available = Object.entries(quality)
          .filter(([_, info]) => info.enabled)
          .map(([period, _]) => parseInt(period));
        setAvailablePeriods(available);

        if (available.length > 0) {
          if (!available.includes(timeRange)) {
            setTimeRange(Math.max(...available));
          }
        } else if (historicalData.length > 0) {
          setAvailablePeriods([7]);
          setTimeRange(7);
        }
      }
    }
  }, [historicalData, fundingInterval, timeRange, assessPeriodAvailability]);

  useEffect(() => {
    if (historicalData.length > 0) {
      const periodDays = showAllData ? 9999 : timeRange;
      const stats = calculatePeriodStats(historicalData, periodDays);
      setPeriodZScore(stats.zScore);
      setPeriodPercentile(stats.percentile);
    }
  }, [historicalData, timeRange, showAllData, calculatePeriodStats]);

  useEffect(() => {
    if (onUpdate && data) {
      onUpdate();
    }
  }, [data, onUpdate]);

  useEffect(() => {
    setCurrentPage(1);
  }, [exchange, symbol]);

  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      const metricElements = document.querySelectorAll('[data-metric]');
      if (metricElements.length > 0) {
        console.assert(metricElements.length === 9, 'VIOLATION: Metric count must be 9');
      }
    }
  }, []);

  const chartData = useMemo(() => {
    if (showAllData) {
      return historicalData;
    }

    if (timeRange && historicalData.length > 0) {
      const now = new Date();
      const cutoffTime = new Date(now.getTime() - timeRange * 24 * 60 * 60 * 1000);
      return historicalData.filter(d => new Date(d.timestamp) >= cutoffTime);
    }

    return historicalData;
  }, [historicalData, timeRange, showAllData]);

  const periodAverage = useMemo(() => {
    const validRates = chartData.filter(d => d.funding_rate !== null);
    if (validRates.length === 0) return null;
    return validRates.reduce((sum, d) => sum + d.funding_rate!, 0) / validRates.length;
  }, [chartData]);

  const exportToCSV = useCallback(() => {
    if (chartData.length === 0) return;

    const headers = ['Timestamp', 'Funding Rate (%)', 'APR (%)'];
    const rows = chartData.map(item => [
      item.timestamp,
      item.funding_rate !== null ? item.funding_rate.toFixed(4) : '',
      item.apr !== null ? item.apr.toFixed(2) : ''
    ].join(','));

    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const filename = isContractView
      ? `${exchange}_${symbol}_funding_${timeRange}d.csv`
      : `${asset}_funding_${timeRange}d.csv`;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  }, [chartData, exchange, symbol, asset, timeRange, isContractView]);

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl p-8 shadow-lg">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="h-96 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl p-8 shadow-lg">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-start">
            <svg className="w-6 h-6 text-red-600 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className="text-lg font-medium text-red-800">Error Loading Data</h3>
              <p className="mt-2 text-sm text-red-600">{error.message}</p>
              <button
                onClick={handleRefresh}
                className="mt-4 px-4 py-2 bg-red-600 text-white hover:bg-red-700 rounded text-sm transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      <div className="px-6 py-4 border-b border-light-border bg-light-bg-secondary">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-2xl font-semibold text-text-primary">
              {symbol} Historical Funding Rates
            </h2>
            <p className="text-sm text-text-secondary mt-1">
              Exchange: {exchange} | Funding Interval: {fundingInterval}h | Base Asset: {baseAsset}
            </p>
          </div>
        </div>
      </div>

      <ContractHistoricalMetrics
        symbol={symbol}
        fundingInterval={fundingInterval}
        contractStats={contractStats}
        periodZScore={periodZScore}
        periodPercentile={periodPercentile}
        timeRange={timeRange}
        showAllData={showAllData}
      />

      <ContractHistoricalFilters
        timeRange={timeRange}
        onTimeRangeChange={setTimeRange}
        dataQuality={dataQuality}
        hasMinimumData={hasMinimumData}
        periodAverage={periodAverage}
        lastUpdate={new Date()}
        onShowPeriodAverageToggle={() => setShowPeriodAverage(!showPeriodAverage)}
        onRefresh={handleRefresh}
        onExportCSV={exportToCSV}
        showPeriodAverage={showPeriodAverage}
      />

      {!hasMinimumData && historicalData.length > 0 && (
        <div className="px-6 py-2 bg-blue-50 border-b border-blue-200">
          <p className="text-sm text-blue-800">
            ℹ️ This appears to be a newly listed contract. Displaying all available historical data
            ({historicalData.filter(d => d.funding_rate !== null).length} data points).
            Period selection will be enabled once 7 days of data is available.
          </p>
        </div>
      )}

      {hasMinimumData && availablePeriods.length === 1 && dataQuality[7]?.completeness < 20 && (
        <div className="px-6 py-2 bg-yellow-50 border-b border-yellow-200">
          <p className="text-sm text-yellow-800">
            ⚠️ Limited historical data available (only {Math.round(dataQuality[7]?.completeness || 0)}% complete).
            Some data points may be missing.
          </p>
        </div>
      )}

      {chartData.length === 0 && historicalData.length === 0 && !isLoading && (
        <div className="px-6 py-8 text-center text-gray-500">
          <p className="text-lg mb-2">No historical data available</p>
          <p className="text-sm">This appears to be a newly listed contract or there may be an issue fetching data.</p>
        </div>
      )}

      {chartData.length > 0 && (
        <ContractHistoricalChart
          data={chartData}
          timeRange={timeRange}
          showAllData={showAllData}
          showPeriodAverage={showPeriodAverage}
        />
      )}

      {historicalData.length > 0 && (
        <ContractHistoricalTable
          data={historicalData}
          currentPage={currentPage}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
        />
      )}
    </div>
  );
};

export default HistoricalFundingViewContract;
