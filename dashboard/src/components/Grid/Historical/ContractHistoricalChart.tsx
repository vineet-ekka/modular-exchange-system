import React, { useMemo } from 'react';
import {
  Area,
  AreaChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { HistoricalDataPoint } from './useContractHistoricalData';

const formatChartTime = (timestamp: string, timeRange?: number): string => {
  const date = new Date(timestamp);
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const month = monthNames[date.getUTCMonth()];
  const day = date.getUTCDate();

  if (timeRange === undefined) {
    const hours = date.getUTCHours();
    const minutes = date.getUTCMinutes();
    const period = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours % 12 || 12;

    const timeString = minutes === 0
      ? `${displayHours} ${period}`
      : `${displayHours}:${minutes.toString().padStart(2, '0')} ${period}`;

    return `${month} ${day}, ${timeString}`;
  }

  if (timeRange <= 1) {
    const hours = date.getUTCHours();
    const minutes = date.getUTCMinutes();
    const period = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours % 12 || 12;

    return minutes === 0
      ? `${displayHours} ${period}`
      : `${displayHours}:${minutes.toString().padStart(2, '0')} ${period}`;
  } else {
    return `${month} ${day}`;
  }
};

const calculateTickInterval = (dataLength: number, timeRange: number): number => {
  const maxTicks = timeRange <= 1 ? 12 : timeRange <= 7 ? 8 : 6;
  const interval = Math.floor(dataLength / maxTicks);
  return Math.max(1, interval);
};

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
  if (active && payload && payload[0]) {
    const data = payload[0].payload;
    const fullTimestamp = formatChartTime(data.timestamp);
    return (
      <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
        <p className="text-xs text-gray-500">{fullTimestamp}</p>
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

interface ContractHistoricalChartProps {
  data: HistoricalDataPoint[];
  timeRange: number;
  showAllData: boolean;
  showPeriodAverage: boolean;
  width?: string;
  height?: number;
}

export const ContractHistoricalChart = React.memo<ContractHistoricalChartProps>(({
  data,
  timeRange,
  showAllData,
  showPeriodAverage,
  width = "100%",
  height = 300
}) => {
  const chartData = useMemo(() => {
    let effectiveTimeRange = timeRange;

    if (showAllData && data.length > 1) {
      const firstDate = new Date(data[0].timestamp);
      const lastDate = new Date(data[data.length - 1].timestamp);
      effectiveTimeRange = Math.ceil((lastDate.getTime() - firstDate.getTime()) / (24 * 60 * 60 * 1000));
    }

    return data.map(item => ({
      ...item,
      displayTime: formatChartTime(item.timestamp, effectiveTimeRange)
    }));
  }, [data, timeRange, showAllData]);

  const periodAverage = useMemo(() => {
    const validRates = chartData.filter(d => d.funding_rate !== null);
    if (validRates.length === 0) return null;
    return validRates.reduce((sum, d) => sum + d.funding_rate!, 0) / validRates.length;
  }, [chartData]);

  const effectiveTimeRange = useMemo(() => {
    if (showAllData && chartData.length > 1) {
      const firstDate = new Date(chartData[0].timestamp);
      const lastDate = new Date(chartData[chartData.length - 1].timestamp);
      return Math.ceil((lastDate.getTime() - firstDate.getTime()) / (24 * 60 * 60 * 1000));
    }
    return timeRange;
  }, [showAllData, chartData, timeRange]);

  if (chartData.length === 0) {
    return null;
  }

  return (
    <div className="px-6 py-4 border-b border-light-border">
      <h3 className="text-lg font-medium text-gray-700 mb-4">Funding Rate Chart</h3>
      <ResponsiveContainer width={width} height={height}>
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="displayTime"
            tick={{ fontSize: 11 }}
            stroke="#6B7280"
            interval={calculateTickInterval(chartData.length, effectiveTimeRange)}
          />
          <YAxis
            tickFormatter={(value) => `${value.toFixed(3)}%`}
            tick={{ fontSize: 12 }}
            stroke="#6B7280"
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <ReferenceLine y={0} stroke="#6B7280" strokeDasharray="3 3" />
          <Area
            type="linear"
            dataKey="funding_rate"
            name="Funding Rate"
            stroke="#10B981"
            strokeWidth={2}
            fill="rgba(16, 185, 129, 0.2)"
            connectNulls={false}
          />
          {showPeriodAverage && periodAverage !== null && (
            <ReferenceLine
              y={periodAverage}
              stroke="#F97316"
              strokeWidth={2}
              strokeDasharray="5 5"
              label={{
                value: `Avg: ${periodAverage.toFixed(4)}%`,
                position: 'right',
                fill: '#F97316',
                fontSize: 12
              }}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}, (prevProps, nextProps) => {
  return (
    prevProps.data === nextProps.data &&
    prevProps.timeRange === nextProps.timeRange &&
    prevProps.showAllData === nextProps.showAllData &&
    prevProps.showPeriodAverage === nextProps.showPeriodAverage
  );
});

ContractHistoricalChart.displayName = 'ContractHistoricalChart';
