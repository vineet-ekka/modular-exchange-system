import React, { useState, useEffect, useCallback, useMemo } from 'react';
import clsx from 'clsx';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend
} from 'recharts';
import { ModernCard } from '../Modern';

interface HistoricalDataPoint {
  timestamp: string;
  displayTime?: string;
  funding_rate: number | null;
  apr: number | null;
}

interface MergedDataPoint {
  timestamp: string;
  displayTime?: string;
  longRate: number | null;
  shortRate: number | null;
  spread: number | null;
}

interface ArbitrageHistoricalChartProps {
  longExchange: string;
  longContract: string;
  shortExchange: string;
  shortContract: string;
  asset: string;
  longIntervalHours?: number;
  shortIntervalHours?: number;
}

const ArbitrageHistoricalChart: React.FC<ArbitrageHistoricalChartProps> = ({
  longExchange,
  longContract,
  shortExchange,
  shortContract,
  asset,
  longIntervalHours = 8,
  shortIntervalHours = 1
}) => {
  const [longData, setLongData] = useState<HistoricalDataPoint[]>([]);
  const [shortData, setShortData] = useState<HistoricalDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState(7); // days
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchHistoricalData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch data for both contracts in parallel
      const [longResponse, shortResponse] = await Promise.all([
        fetch(
          `http://localhost:8000/api/historical-funding-by-contract/${longExchange}/${longContract}?days=30`
        ),
        fetch(
          `http://localhost:8000/api/historical-funding-by-contract/${shortExchange}/${shortContract}?days=30`
        )
      ]);

      if (!longResponse.ok || !shortResponse.ok) {
        throw new Error('Failed to fetch historical data');
      }

      const [longResult, shortResult] = await Promise.all([
        longResponse.json(),
        shortResponse.json()
      ]);

      // Process data - convert to percentage
      const processedLongData = longResult.data?.map((item: any) => ({
        timestamp: item.timestamp,
        displayTime: new Date(item.timestamp).toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          timeZone: 'UTC'
        }),
        funding_rate: item.funding_rate !== null ? item.funding_rate * 100 : null,
        apr: item.apr || null
      })) || [];

      const processedShortData = shortResult.data?.map((item: any) => ({
        timestamp: item.timestamp,
        displayTime: new Date(item.timestamp).toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          timeZone: 'UTC'
        }),
        funding_rate: item.funding_rate !== null ? item.funding_rate * 100 : null,
        apr: item.apr || null
      })) || [];

      // Reverse for chronological order
      setLongData(processedLongData.reverse());
      setShortData(processedShortData.reverse());
      setLastUpdate(new Date());

    } catch (err) {
      console.error('Error fetching historical data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [longExchange, longContract, shortExchange, shortContract]);

  useEffect(() => {
    fetchHistoricalData();
  }, [fetchHistoricalData]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchHistoricalData();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchHistoricalData]);

  // Merge data by timestamp with normalization to longer interval
  const mergedData = useMemo(() => {
    // Use the dynamic funding intervals passed as props
    const normalizeInterval = Math.max(longIntervalHours, shortIntervalHours); // Use the longer interval

    // Function to normalize timestamp to interval boundary
    const normalizeTimestamp = (timestamp: string, intervalHours: number) => {
      const date = new Date(timestamp);
      const hours = date.getUTCHours();
      const normalizedHours = Math.floor(hours / intervalHours) * intervalHours;
      date.setUTCHours(normalizedHours, 0, 0, 0);
      return date.toISOString();
    };

    // Create maps for each exchange's data
    const longDataMap = new Map<string, HistoricalDataPoint>();
    const shortDataMap = new Map<string, HistoricalDataPoint>();

    // Populate long data map with normalized timestamps
    longData.forEach(item => {
      const normalizedTime = normalizeTimestamp(item.timestamp, normalizeInterval);
      // If we already have data for this normalized time, keep the most recent
      const existing = longDataMap.get(normalizedTime);
      if (!existing || new Date(item.timestamp) > new Date(existing.timestamp)) {
        longDataMap.set(normalizedTime, item);
      }
    });

    // Populate short data map with normalized timestamps
    shortData.forEach(item => {
      const normalizedTime = normalizeTimestamp(item.timestamp, normalizeInterval);
      // If we already have data for this normalized time, keep the most recent
      const existing = shortDataMap.get(normalizedTime);
      if (!existing || new Date(item.timestamp) > new Date(existing.timestamp)) {
        shortDataMap.set(normalizedTime, item);
      }
    });

    // Get all unique normalized timestamps
    const allTimestamps = new Set([...longDataMap.keys(), ...shortDataMap.keys()]);

    // Build merged data with forward-fill for missing values
    const mergedPoints: MergedDataPoint[] = [];
    let lastLongRate: number | null = null;
    let lastShortRate: number | null = null;

    // Sort timestamps
    const sortedTimestamps = Array.from(allTimestamps).sort();

    sortedTimestamps.forEach(timestamp => {
      const longPoint = longDataMap.get(timestamp);
      const shortPoint = shortDataMap.get(timestamp);

      // Use current value or forward-fill from last known value
      const currentLongRate = longPoint?.funding_rate ?? lastLongRate;
      const currentShortRate = shortPoint?.funding_rate ?? lastShortRate;

      // Update last known values
      if (longPoint?.funding_rate !== null && longPoint?.funding_rate !== undefined) {
        lastLongRate = longPoint.funding_rate;
      }
      if (shortPoint?.funding_rate !== null && shortPoint?.funding_rate !== undefined) {
        lastShortRate = shortPoint.funding_rate;
      }

      // Calculate spread only if both values are available
      let spread: number | null = null;
      if (currentLongRate !== null && currentShortRate !== null) {
        spread = currentShortRate - currentLongRate;
      }

      mergedPoints.push({
        timestamp,
        displayTime: new Date(timestamp).toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          timeZone: 'UTC'
        }),
        longRate: currentLongRate,
        shortRate: currentShortRate,
        spread
      });
    });

    // Filter by time range
    const now = new Date();
    const cutoffTime = new Date(now.getTime() - timeRange * 24 * 60 * 60 * 1000);

    return mergedPoints
      .filter(d => new Date(d.timestamp) >= cutoffTime)
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [longData, shortData, timeRange, longIntervalHours, shortIntervalHours]);

  // Calculate statistics
  const stats = useMemo(() => {
    const longRates = mergedData
      .map(d => d.longRate)
      .filter(r => r !== null) as number[];
    const shortRates = mergedData
      .map(d => d.shortRate)
      .filter(r => r !== null) as number[];
    const spreads = mergedData
      .map(d => d.spread)
      .filter(s => s !== null) as number[];

    const calculateStats = (values: number[]) => {
      if (values.length === 0) return { avg: 0, min: 0, max: 0 };
      const avg = values.reduce((a, b) => a + b, 0) / values.length;
      const min = Math.min(...values);
      const max = Math.max(...values);
      return { avg, min, max };
    };

    return {
      long: calculateStats(longRates),
      short: calculateStats(shortRates),
      spread: calculateStats(spreads),
      dataPoints: mergedData.length
    };
  }, [mergedData]);

  const exportToCSV = () => {
    if (mergedData.length === 0) return;

    const headers = ['Timestamp', `${longExchange} ${longContract} (%)`, `${shortExchange} ${shortContract} (%)`, 'Spread (%)'];
    const rows = mergedData.map(item => {
      return [
        item.timestamp,
        item.longRate !== null ? item.longRate.toFixed(4) : '',
        item.shortRate !== null ? item.shortRate.toFixed(4) : '',
        item.spread !== null ? item.spread.toFixed(4) : ''
      ].join(',');
    });

    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${asset}_arbitrage_funding_${timeRange}d.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload[0]) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
          <p className="text-xs text-gray-500 mb-1">{data.displayTime}</p>
          <div className="space-y-1">
            <p className="text-sm">
              <span className="inline-block w-3 h-3 bg-green-500 rounded-full mr-2"></span>
              <span className="font-medium">Long ({longExchange}):</span>{' '}
              {data.longRate !== null ? `${data.longRate.toFixed(4)}%` : 'N/A'}
            </p>
            <p className="text-sm">
              <span className="inline-block w-3 h-3 bg-red-500 rounded-full mr-2"></span>
              <span className="font-medium">Short ({shortExchange}):</span>{' '}
              {data.shortRate !== null ? `${data.shortRate.toFixed(4)}%` : 'N/A'}
            </p>
            {data.spread !== null && (
              <p className="text-sm pt-1 border-t border-gray-200">
                <span className="font-medium">Spread:</span>{' '}
                <span className={clsx(
                  'font-bold',
                  data.spread > 0 ? 'text-green-600' : 'text-red-600'
                )}>
                  {data.spread.toFixed(4)}%
                </span>
              </p>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <ModernCard variant="elevated" padding="xl">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="h-64 bg-gray-100 rounded"></div>
        </div>
      </ModernCard>
    );
  }

  if (error) {
    return (
      <ModernCard variant="elevated" padding="xl">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-red-800">Error Loading Chart Data</h3>
          <p className="mt-2 text-sm text-red-600">{error}</p>
          <button
            onClick={fetchHistoricalData}
            className="mt-4 px-4 py-2 bg-red-600 text-white hover:bg-red-700 rounded text-sm transition-colors"
          >
            Try Again
          </button>
        </div>
      </ModernCard>
    );
  }

  return (
    <ModernCard variant="elevated" padding="xl">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-xl font-bold text-text-primary">
              Historical Funding Rate Comparison
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-text-tertiary">
                Data normalized to {Math.max(longIntervalHours, shortIntervalHours)}-hour intervals for alignment
              </span>
              <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">
                Forward-fill enabled
              </span>
            </div>
          </div>
          <div className="text-sm text-text-tertiary">
            Last updated: {lastUpdate.toLocaleTimeString('en-US', { timeZone: 'UTC', timeZoneName: 'short' })}
          </div>
        </div>

        {/* Time Range Selector */}
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600 mr-2">Time Period:</span>
            {[1, 7, 14, 30].map(period => (
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
              </button>
            ))}
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

        {/* Chart */}
        {mergedData.length > 0 ? (
          <div className="bg-white rounded-lg p-4">
            <ResponsiveContainer width="100%" height={350}>
              <LineChart
                data={mergedData}
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
                <Legend />
                <ReferenceLine y={0} stroke="#6B7280" strokeDasharray="3 3" />

                {/* Long position line (negative funding is good) */}
                <Line
                  type="monotone"
                  dataKey="longRate"
                  name={`Long (${longExchange})`}
                  stroke="#10B981"
                  strokeWidth={2}
                  dot={false}
                  connectNulls={true}
                />

                {/* Short position line (positive funding is good) */}
                <Line
                  type="monotone"
                  dataKey="shortRate"
                  name={`Short (${shortExchange})`}
                  stroke="#EF4444"
                  strokeWidth={2}
                  dot={false}
                  connectNulls={true}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="bg-gray-50 rounded-lg p-8 text-center text-gray-500">
            No data available for the selected period
          </div>
        )}

        {/* Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-light-border">
          {/* Long Statistics */}
          <div className="bg-green-50 rounded-lg p-3">
            <h4 className="text-sm font-medium text-green-800 mb-2">
              Long Position ({longExchange})
            </h4>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-green-600">Average:</span>
                <span className="font-medium text-green-800">{stats.long.avg.toFixed(4)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-green-600">Min:</span>
                <span className="font-medium text-green-800">{stats.long.min.toFixed(4)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-green-600">Max:</span>
                <span className="font-medium text-green-800">{stats.long.max.toFixed(4)}%</span>
              </div>
            </div>
          </div>

          {/* Short Statistics */}
          <div className="bg-red-50 rounded-lg p-3">
            <h4 className="text-sm font-medium text-red-800 mb-2">
              Short Position ({shortExchange})
            </h4>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-red-600">Average:</span>
                <span className="font-medium text-red-800">{stats.short.avg.toFixed(4)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-red-600">Min:</span>
                <span className="font-medium text-red-800">{stats.short.min.toFixed(4)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-red-600">Max:</span>
                <span className="font-medium text-red-800">{stats.short.max.toFixed(4)}%</span>
              </div>
            </div>
          </div>

          {/* Spread Statistics */}
          <div className="bg-blue-50 rounded-lg p-3">
            <h4 className="text-sm font-medium text-blue-800 mb-2">
              Spread Statistics
            </h4>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-blue-600">Average:</span>
                <span className="font-medium text-blue-800">{stats.spread.avg.toFixed(4)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-blue-600">Min:</span>
                <span className="font-medium text-blue-800">{stats.spread.min.toFixed(4)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-blue-600">Max:</span>
                <span className="font-medium text-blue-800">{stats.spread.max.toFixed(4)}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Data Points Info */}
        <div className="text-xs text-text-tertiary text-center">
          <div>Showing {stats.dataPoints} normalized data points for the last {timeRange} day{timeRange > 1 ? 's' : ''}</div>
          <div className="mt-1">
            Original data: {longExchange} updates every {longIntervalHours}h • {shortExchange} updates every {shortIntervalHours}h
          </div>
        </div>
      </div>
    </ModernCard>
  );
};

export default ArbitrageHistoricalChart;