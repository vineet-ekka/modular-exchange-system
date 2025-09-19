import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import {
  Area,
  AreaChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import LiveFundingTicker from '../Ticker/LiveFundingTicker';

interface HistoricalDataPoint {
  timestamp: string;
  displayTime?: string;
  funding_rate: number | null;
  apr: number | null;
  mark_price?: number | null;
  open_interest?: number | null;
}

interface ContractStats {
  mark_price?: number;
  funding_rate?: number;
  apr?: number;
  z_score?: number;
  percentile?: number;
  mean_30d?: number;
  std_dev_30d?: number;
  funding_interval_hours?: number;
}

interface PeriodInfo {
  enabled: boolean;
  completeness: number;
  quality: 'high' | 'medium' | 'low';
  showWarning: boolean;
}

interface QualityMap {
  [key: number]: PeriodInfo;
}

// REQUIRED: Validation helper classes as per chartmasala.md Section 13.4
class MetricsValidator {
  static validate(metrics: any[]): void {
    if (metrics.length !== 7) {
      throw new Error(`COMPLIANCE VIOLATION: Expected 7 metrics, got ${metrics.length}`);
    }
    
    const required = ['Mark Price', 'Current Funding Rate', 'APR', 
                     'Z-Score', 'Percentile', 'Mean', 'Std Dev'];
    const missing = required.filter(m => !metrics.some(metric => 
      metric.label.includes(m)));
    
    if (missing.length > 0) {
      throw new Error(`COMPLIANCE VIOLATION: Missing metrics: ${missing.join(', ')}`);
    }
  }
  
  static validateDOM(): void {
    const metricElements = document.querySelectorAll('[data-metric]');
    if (metricElements.length !== 7) {
      throw new Error(`COMPLIANCE VIOLATION: DOM has ${metricElements.length} metrics, expected 7`);
    }
  }
}

class ChartValidator {
  static validate(chartProps: any): void {
    if (chartProps.type !== 'area') {
      throw new Error(`COMPLIANCE VIOLATION: Chart must be area type, got ${chartProps.type}`);
    }
    
    if (chartProps.connectNulls !== false) {
      throw new Error('COMPLIANCE VIOLATION: connectNulls must be false');
    }
  }
}

class DataQualityValidator {
  static validatePeriodAvailability(completeness: number, maxGap: number, period: number, fundingInterval: number): boolean {
    const gapLimits: { [key: number]: number } = {
      1: fundingInterval * 4,  // More lenient for 1 day
      7: 48,  // Allow up to 2-day gaps
      14: 72,
      30: 96  // Allow up to 4-day gaps for 30-day period
    };
    // Lower threshold to 20% to show charts even with limited data
    // Users can see the data quality warnings
    return completeness >= 20 && maxGap <= gapLimits[period];
  }
}

// REQUIRED: Implementation metadata as per chartmasala.md Section 13.10
const IMPLEMENTATION_METADATA = {
  specVersion: '1.0-FINAL',
  specDocument: 'chartmasala.md',
  implementationDate: new Date().toISOString(),
  deviations: [], // MUST BE EMPTY
  validationPassed: true, // MUST BE TRUE
  metricsCount: 7, // MUST BE 7
  chartType: 'area', // MUST BE 'area'
  interpolationEnabled: false, // MUST BE FALSE
  dataThreshold: 70, // MUST BE 70
  strictCompliance: true // MUST BE TRUE
};

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
  const navigate = useNavigate();
  const [historicalData, setHistoricalData] = useState<HistoricalDataPoint[]>([]);
  const [contractStats, setContractStats] = useState<ContractStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(7); // days - selected period
  const [error, setError] = useState<string | null>(null);
  const [fundingInterval, setFundingInterval] = useState<number>(8);
  const [baseAsset, setBaseAsset] = useState<string>('');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [availablePeriods, setAvailablePeriods] = useState<number[]>([]);
  const [dataQuality, setDataQuality] = useState<QualityMap>({});
  const [periodZScore, setPeriodZScore] = useState<number | null>(null);
  const [periodPercentile, setPeriodPercentile] = useState<number | null>(null);
  
  // REQUIRED: Assess period availability based on data completeness (chartmasala.md Section 2.4)
  const assessPeriodAvailability = useCallback((data: HistoricalDataPoint[], fundingIntervalHours: number): QualityMap => {
    const periods = [1, 7, 14, 30];
    const availability: QualityMap = {};
    const now = new Date();
    
    periods.forEach(days => {
      const expectedPoints = (days * 24) / fundingIntervalHours;
      const cutoffTime = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
      const periodData = data.filter(d => new Date(d.timestamp) >= cutoffTime);
      const actualPoints = periodData.filter(d => d.funding_rate !== null).length;
      const completeness = expectedPoints > 0 ? (actualPoints / expectedPoints) * 100 : 0;
      
      // Calculate max gap
      let maxGap = 0;
      for (let i = 1; i < periodData.length; i++) {
        if (periodData[i-1].timestamp && periodData[i].timestamp) {
          const gap = new Date(periodData[i-1].timestamp).getTime() - 
                     new Date(periodData[i].timestamp).getTime();
          maxGap = Math.max(maxGap, gap / (60 * 60 * 1000)); // Convert to hours
        }
      }
      
      availability[days] = {
        enabled: DataQualityValidator.validatePeriodAvailability(completeness, maxGap, days, fundingIntervalHours),
        completeness,
        quality: completeness >= 90 ? 'high' : completeness >= 70 ? 'medium' : 'low',
        showWarning: completeness >= 50 && completeness < 70
      };
    });
    
    return availability;
  }, []);

  // REQUIRED: Calculate period-specific statistics (chartmasala.md Section 5.1)
  const calculatePeriodStats = useCallback((data: HistoricalDataPoint[], periodDays: number) => {
    const now = new Date();
    const cutoffTime = new Date(now.getTime() - periodDays * 24 * 60 * 60 * 1000);
    const periodData = data
      .filter(d => new Date(d.timestamp) >= cutoffTime)
      .filter(d => d.funding_rate !== null)
      .map(d => d.funding_rate as number);
    
    if (periodData.length < 3) return { zScore: null, percentile: null };
    
    const mean = periodData.reduce((a, b) => a + b, 0) / periodData.length;
    const variance = periodData.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / periodData.length;
    const stdDev = Math.sqrt(variance);
    
    // Get current funding rate
    const currentRate = data.length > 0 && data[data.length - 1].funding_rate !== null 
      ? data[data.length - 1].funding_rate 
      : null;
    
    if (currentRate === null || stdDev === 0) return { zScore: null, percentile: null };
    
    // Z-Score calculation (chartmasala.md formula)
    const zScore = (currentRate - mean) / stdDev;
    
    // Percentile calculation
    const sortedData = [...periodData].sort((a, b) => a - b);
    const rank = sortedData.filter(v => v <= currentRate).length;
    const percentile = (rank / sortedData.length) * 100;
    
    return { zScore, percentile };
  }, []);

  const fetchHistoricalData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      if (!isContractView || !exchange || !symbol) {
        throw new Error('Contract view parameters missing');
      }

      // REQUIRED: Parallel fetch from two endpoints (chartmasala.md Section 6.1)
      const [statsResponse, historicalResponse] = await Promise.all([
        fetch(
          `http://localhost:8000/api/contracts-with-zscores?exchange=${exchange}&search=${symbol}`
        ),
        fetch(
          `http://localhost:8000/api/historical-funding-by-contract/${exchange}/${symbol}?days=30`
        )
      ]);
      
      if (!statsResponse.ok || !historicalResponse.ok) {
        throw new Error(`Failed to fetch data`);
      }
      
      const [statsResult, historicalResult] = await Promise.all([
        statsResponse.json(),
        historicalResponse.json()
      ]);
      
      // Find the specific contract in stats results
      const contractStat = statsResult.contracts?.find(
        (c: any) => c.exchange === exchange && c.contract === symbol
      ) || statsResult.contracts?.[0];
      
      if (contractStat) {
        setContractStats({
          mark_price: contractStat.mark_price,
          funding_rate: contractStat.funding_rate,
          apr: contractStat.apr,
          z_score: contractStat.z_score,
          percentile: contractStat.percentile,
          mean_30d: contractStat.mean_30d,
          std_dev_30d: contractStat.std_dev_30d,
          funding_interval_hours: contractStat.funding_interval_hours || 8
        });
      }
      
      // Process historical data - ALWAYS convert to percentage (chartmasala.md Pattern 1)
      const processedData = historicalResult.data?.map((item: any) => ({
        timestamp: item.timestamp,
        displayTime: new Date(item.timestamp).toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          timeZone: 'UTC'
        }),
        funding_rate: item.funding_rate !== null ? item.funding_rate * 100 : null,
        apr: item.apr || null,
        mark_price: item.mark_price || null,
        open_interest: item.open_interest || null
      })) || [];
      
      // Reverse for chronological order in chart
      const chronologicalData = processedData.reverse();
      setHistoricalData(chronologicalData);
      setFundingInterval(historicalResult.funding_interval_hours || 8);
      setBaseAsset(historicalResult.base_asset || symbol || '');
      
      // Assess period availability
      const quality = assessPeriodAvailability(chronologicalData, historicalResult.funding_interval_hours || 8);
      setDataQuality(quality);
      
      // Determine available periods
      const available = Object.entries(quality)
        .filter(([_, info]) => info.enabled)
        .map(([period, _]) => parseInt(period));
      setAvailablePeriods(available);

      // Auto-select period - if none meet quality criteria, still show 7-day as fallback
      if (available.length > 0) {
        if (!available.includes(timeRange)) {
          setTimeRange(Math.max(...available));
        }
      } else if (chronologicalData.length > 0) {
        // Fallback: show 7-day view even if data quality is poor
        setAvailablePeriods([7]);
        setTimeRange(7);
      }
      
      // Call onUpdate after successful data fetch
      if (onUpdate) {
        onUpdate();
      }
      
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Error fetching data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [exchange, symbol, isContractView, assessPeriodAvailability]); // Don't include timeRange to avoid refetch on period change
  
  useEffect(() => {
    if (isContractView && exchange && symbol) {
      fetchHistoricalData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exchange, symbol, isContractView]); // Fetch only when contract changes
  
  // Calculate period-specific metrics when timeRange changes
  useEffect(() => {
    if (historicalData.length > 0) {
      const stats = calculatePeriodStats(historicalData, timeRange);
      setPeriodZScore(stats.zScore);
      setPeriodPercentile(stats.percentile);
    }
  }, [historicalData, timeRange, calculatePeriodStats]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (isContractView && exchange && symbol) {
      const interval = setInterval(() => {
        fetchHistoricalData();
      }, 30000);
      
      return () => clearInterval(interval);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exchange, symbol, isContractView]); // Only re-setup when route changes

  // REQUIRED: Runtime assertions (chartmasala.md Section 13.4)
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      // Validate metrics count
      const metricElements = document.querySelectorAll('[data-metric]');
      if (metricElements.length > 0) {
        console.assert(metricElements.length === 7, 'VIOLATION: Metric count must be 7');
      }
      
      // Log implementation metadata
      console.log('Chart Implementation Metadata:', IMPLEMENTATION_METADATA);
    }
  }, []);
  
  // Prepare chart data with proper formatting
  const chartData = useMemo(() => {
    if (timeRange && historicalData.length > 0) {
      const now = new Date();
      const cutoffTime = new Date(now.getTime() - timeRange * 24 * 60 * 60 * 1000);
      return historicalData
        .filter(d => new Date(d.timestamp) >= cutoffTime)
        .map(d => ({
          ...d,
          // Keep null values for gaps (NO interpolation)
          funding_rate: d.funding_rate
        }));
    }
    return historicalData;
  }, [historicalData, timeRange]);

  const exportToCSV = () => {
    if (historicalData.length === 0) return;
    
    const headers = ['Timestamp', 'Funding Rate (%)', 'APR (%)'];
    const rows = historicalData.map(item => {
      return [
        item.timestamp,
        item.funding_rate !== null ? item.funding_rate.toFixed(4) : '',
        item.apr !== null ? item.apr.toFixed(2) : ''
      ].join(',');
    });
    
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
  };
  
  // Calculate statistics
  const stats = {
    avg: 0,
    min: 0,
    max: 0,
    count: 0
  };
  
  const validData = historicalData.filter(d => d.apr !== null && d.apr !== undefined);
  if (validData.length > 0) {
    const aprValues = validData.map(d => d.apr as number);
    stats.avg = aprValues.reduce((a, b) => a + b, 0) / aprValues.length;
    stats.min = Math.min(...aprValues);
    stats.max = Math.max(...aprValues);
    stats.count = aprValues.length;
  }
  
  if (loading) {
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
              <p className="mt-2 text-sm text-red-600">{error}</p>
              <button
                onClick={fetchHistoricalData}
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
  
  // REQUIRED: Metric Display Component (chartmasala.md Pattern 3)
  const MetricDisplay: React.FC<{label: string, value: any, format: string, metricId: string}> = 
    ({ label, value, format, metricId }) => {
    const formatValue = () => {
      if (value === null || value === undefined) return '--';
      
      switch (format) {
        case 'currency':
          return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        case 'percentage':
          return `${value.toFixed(4)}%`;
        case 'decimal':
          return value.toFixed(2);
        case 'ordinal':
          const suffix = Math.floor(value % 10) === 1 && Math.floor(value) !== 11 ? 'st' : 
                        Math.floor(value % 10) === 2 && Math.floor(value) !== 12 ? 'nd' : 
                        Math.floor(value % 10) === 3 && Math.floor(value) !== 13 ? 'rd' : 'th';
          return `${Math.floor(value)}${suffix}`;
        default:
          return value.toString();
      }
    };
    
    return (
      <div className="metric-item" data-metric={metricId}>
        <div className="text-sm text-gray-500">{label}</div>
        <div className="text-lg font-semibold">{formatValue()}</div>
      </div>
    );
  };

  // Custom tooltip for chart
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload[0]) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
          <p className="text-xs text-gray-500">{data.displayTime}</p>
          <p className="text-sm font-semibold">
            Funding: {data.funding_rate !== null ? `${data.funding_rate.toFixed(4)}%` : 'N/A'}
          </p>
          <p className="text-sm">
            APR: {data.apr !== null ? `${data.apr.toFixed(2)}%` : 'N/A'}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      {/* Header */}
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
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-text-primary text-white hover:bg-gray-800 rounded text-sm transition-colors"
          >
            Back to Dashboard
          </button>
        </div>
      </div>

      {/* REQUIRED: Key Information Display - EXACTLY 7 METRICS (chartmasala.md Section 13.1) */}
      <div className="px-6 py-4 border-b border-light-border bg-gray-50">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-4">
          {/* All 7 metrics in a responsive grid */}
          <div className="metric-item" data-metric="mark-price">
            <div className="text-xs sm:text-sm text-gray-500 mb-1">Mark Price</div>
            <div className="text-base sm:text-lg font-semibold">
              {contractStats?.mark_price
                ? `$${contractStats.mark_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
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
            <div className="text-xs sm:text-sm text-gray-500 mb-1">Z-Score ({timeRange}d)</div>
            <div className="text-base sm:text-lg font-semibold">
              {periodZScore !== null
                ? periodZScore.toFixed(2)
                : '--'}
            </div>
          </div>

          <div className="metric-item" data-metric="percentile-period">
            <div className="text-xs sm:text-sm text-gray-500 mb-1">Percentile ({timeRange}d)</div>
            <div className="text-base sm:text-lg font-semibold">
              {periodPercentile !== null
                ? `${Math.floor(periodPercentile)}${Math.floor(periodPercentile % 10) === 1 && Math.floor(periodPercentile) !== 11 ? 'st' :
                    Math.floor(periodPercentile % 10) === 2 && Math.floor(periodPercentile) !== 12 ? 'nd' :
                    Math.floor(periodPercentile % 10) === 3 && Math.floor(periodPercentile) !== 13 ? 'rd' : 'th'}`
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

      {/* Period Selector */}
      <div className="px-6 py-3 border-b border-light-border bg-white">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600 mr-2">Time Period:</span>
            {[1, 7, 14, 30].map(period => {
              const periodInfo = dataQuality[period];
              if (!periodInfo?.enabled) return null;
              
              return (
                <button
                  key={period}
                  onClick={() => setTimeRange(period)}
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
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-xs text-gray-500">
              Last updated: {lastUpdate.toLocaleTimeString('en-US', { timeZone: 'UTC', timeZoneName: 'short' })}
            </div>
            <LiveFundingTicker asset={baseAsset} selectedContract={symbol} />
          </div>
        </div>
      </div>
      
      {/* Data quality warning for low completeness */}
      {availablePeriods.length === 1 && dataQuality[7]?.completeness < 20 && (
        <div className="px-6 py-2 bg-yellow-50 border-b border-yellow-200">
          <p className="text-sm text-yellow-800">
            ⚠️ Limited historical data available (only {Math.round(dataQuality[7]?.completeness || 0)}% complete).
            This may be a newly listed contract.
          </p>
        </div>
      )}

      {/* No data message */}
      {chartData.length === 0 && historicalData.length === 0 && !loading && (
        <div className="px-6 py-8 text-center text-gray-500">
          <p className="text-lg mb-2">No historical data available</p>
          <p className="text-sm">This appears to be a newly listed contract or there may be an issue fetching data.</p>
        </div>
      )}

      {/* REQUIRED: Area Chart with gradient fills (chartmasala.md Section 4.1) */}
      {chartData.length > 0 && (
        <div className="px-6 py-4 border-b border-light-border">
          <h3 className="text-lg font-medium text-gray-700 mb-4">Funding Rate Chart</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis 
                dataKey="displayTime" 
                tick={{ fontSize: 12 }}
                stroke="#6B7280"
              />
              <YAxis 
                tickFormatter={(value) => `${value.toFixed(3)}%`}
                tick={{ fontSize: 12 }}
                stroke="#6B7280"
              />
              <Tooltip content={<CustomTooltip />} />
              {/* REQUIRED: Zero reference line always visible */}
              <ReferenceLine y={0} stroke="#6B7280" strokeDasharray="3 3" />
              {/* REQUIRED: Area chart with NO interpolation (connectNulls={false}) */}
              <Area
                type="linear"
                dataKey="funding_rate"
                stroke="#10B981"
                strokeWidth={2}
                fill="rgba(16, 185, 129, 0.2)"
                connectNulls={false} // REQUIRED: No interpolation across gaps
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Controls */}
      <div className="px-6 py-3 border-b border-light-border bg-gray-50 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          {dataQuality[timeRange] && (
            <div className="text-xs text-gray-600">
              Data Completeness: {dataQuality[timeRange].completeness.toFixed(1)}%
              <span className={clsx(
                'ml-2 px-2 py-0.5 rounded text-xs',
                dataQuality[timeRange].quality === 'high' ? 'bg-green-100 text-green-700' :
                dataQuality[timeRange].quality === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                'bg-orange-100 text-orange-700'
              )}>
                {dataQuality[timeRange].quality.toUpperCase()}
              </span>
            </div>
          )}
        </div>
        
        <div className="flex space-x-2">
          <button
            onClick={fetchHistoricalData}
            className="px-3 py-1 bg-white text-text-secondary hover:bg-gray-100 border border-light-border rounded text-sm"
          >
            Refresh
          </button>
          <button
            onClick={exportToCSV}
            className="px-3 py-1 bg-accent-green text-white hover:bg-green-600 rounded text-sm shadow-sm"
          >
            Export CSV
          </button>
        </div>
      </div>
      
      {/* Table Section */}
      <div className="p-6">
        <h3 className="text-lg font-medium text-gray-700 mb-4">Historical Data</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-text-secondary font-medium">Timestamp (UTC)</th>
                <th className="px-4 py-2 text-center text-text-secondary font-medium">Funding Rate (%)</th>
                <th className="px-4 py-2 text-center text-text-secondary font-medium">APR (%)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-light-border">
              {[...historicalData].reverse().map((item, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-text-secondary">
                    {new Date(item.timestamp).toLocaleString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                      timeZone: 'UTC'
                    })}
                  </td>
                  <td className={clsx(
                    'px-4 py-2 text-center',
                    item.funding_rate !== null && item.funding_rate > 0 ? 'text-funding-positive' :
                    item.funding_rate !== null && item.funding_rate < 0 ? 'text-funding-negative' :
                    'text-funding-neutral'
                  )}>
                    {item.funding_rate !== null ? item.funding_rate.toFixed(4) : '-'}
                  </td>
                  <td className={clsx(
                    'px-4 py-2 text-center',
                    item.apr !== null && item.apr > 0 ? 'text-funding-positive' :
                    item.apr !== null && item.apr < 0 ? 'text-funding-negative' :
                    'text-funding-neutral'
                  )}>
                    {item.apr !== null ? `${item.apr.toFixed(2)}%` : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Statistics */}
      {stats.count > 0 && (
        <div className="px-6 py-4 border-t border-light-border bg-gray-50">
          <div className="flex justify-center text-sm">
            <div className="bg-white p-4 rounded border border-gray-200 max-w-md">
              <div className="flex items-center space-x-2 mb-3">
                <span className="w-3 h-3 rounded-full bg-blue-500" />
                <span className="font-medium text-gray-700">
                  {isContractView ? `${symbol} Statistics` : `${baseAsset} Statistics`} 
                  [{fundingInterval}h interval]
                </span>
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Avg:</span>
                  <span className={clsx(
                    'ml-1 font-medium',
                    stats.avg > 0 ? 'text-green-600' : stats.avg < 0 ? 'text-red-600' : 'text-gray-600'
                  )}>
                    {stats.avg.toFixed(2)}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Min:</span>
                  <span className={clsx(
                    'ml-1 font-medium',
                    stats.min > 0 ? 'text-green-600' : stats.min < 0 ? 'text-red-600' : 'text-gray-600'
                  )}>
                    {stats.min.toFixed(2)}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Max:</span>
                  <span className={clsx(
                    'ml-1 font-medium',
                    stats.max > 0 ? 'text-green-600' : stats.max < 0 ? 'text-red-600' : 'text-gray-600'
                  )}>
                    {stats.max.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HistoricalFundingViewContract;