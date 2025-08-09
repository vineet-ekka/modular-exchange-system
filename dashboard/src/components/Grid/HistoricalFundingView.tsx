import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import clsx from 'clsx';

interface HistoricalDataPoint {
  timestamp: string;
  [exchange: string]: string | number | null;
}

interface HistoricalFundingViewProps {
  asset: string;
  onClose: () => void;
}

const EXCHANGE_COLORS: Record<string, string> = {
  'Binance': '#F0B90B'
};

const HistoricalFundingView: React.FC<HistoricalFundingViewProps> = ({ asset, onClose }) => {
  const [historicalData, setHistoricalData] = useState<HistoricalDataPoint[]>([]);
  const [exchanges, setExchanges] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(7); // days
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    const fetchHistoricalData = async () => {
      setLoading(true);
      try {
        const response = await fetch(
          `http://localhost:8000/api/historical-funding-by-asset/${asset}?days=${timeRange}`
        );
        const result = await response.json();
        
        if (result.data) {
          // Process data for chart
          const processedData = result.data.map((item: HistoricalDataPoint) => {
            const point: any = {
              timestamp: new Date(item.timestamp).toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
              })
            };
            
            // Convert funding rates to percentages
            result.exchanges.forEach((exchange: string) => {
              const value = item[exchange];
              point[exchange] = value !== null ? (value as number) * 100 : null;
            });
            
            return point;
          });
          
          setHistoricalData(processedData);
          setExchanges(result.exchanges || []);
        }
      } catch (error) {
        console.error('Error fetching historical data:', error);
      } finally {
        setLoading(false);
      }
    };

    if (asset) {
      fetchHistoricalData();
    }
  }, [asset, timeRange]);

  const exportToCSV = () => {
    if (historicalData.length === 0) return;

    const headers = ['Timestamp', ...exchanges];
    const rows = historicalData.map(item => {
      const row = [item.timestamp];
      exchanges.forEach(exchange => {
        const value = item[exchange];
        row.push(value !== null ? value.toString() : '');
      });
      return row.join(',');
    });

    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${asset}_funding_rates_${timeRange}d.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-gray-800 rounded-xl p-8 max-w-6xl w-full mx-4">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-gray-700 rounded w-1/3"></div>
            <div className="h-96 bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl max-w-7xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-semibold text-gray-100">
              {asset} Historical Funding Rates
            </h2>
            <p className="text-sm text-gray-400 mt-1">
              Comparison across {exchanges.length} exchanges
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Controls */}
        <div className="px-6 py-3 border-b border-gray-700 flex justify-between items-center">
          <div className="flex space-x-2">
            {[1, 7, 30].map(days => (
              <button
                key={days}
                onClick={() => setTimeRange(days)}
                className={clsx(
                  'px-3 py-1 rounded text-sm',
                  timeRange === days
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                )}
              >
                {days}D
              </button>
            ))}
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => setShowTable(!showTable)}
              className="px-3 py-1 bg-gray-700 text-gray-300 hover:bg-gray-600 rounded text-sm"
            >
              {showTable ? 'Show Chart' : 'Show Table'}
            </button>
            <button
              onClick={exportToCSV}
              className="px-3 py-1 bg-green-600 text-white hover:bg-green-700 rounded text-sm"
            >
              Export CSV
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {!showTable ? (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={historicalData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="timestamp" 
                  stroke="#9CA3AF"
                  tick={{ fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis 
                  stroke="#9CA3AF"
                  tick={{ fontSize: 12 }}
                  label={{ 
                    value: 'Funding Rate (%)', 
                    angle: -90, 
                    position: 'insideLeft',
                    style: { fill: '#9CA3AF' }
                  }}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                  labelStyle={{ color: '#E5E7EB' }}
                  formatter={(value: any) => 
                    value !== null ? `${value.toFixed(4)}%` : 'N/A'
                  }
                />
                <Legend 
                  wrapperStyle={{ paddingTop: '20px' }}
                  iconType="line"
                />
                {exchanges.map(exchange => (
                  <Line
                    key={exchange}
                    type="monotone"
                    dataKey={exchange}
                    stroke={EXCHANGE_COLORS[exchange] || '#6B7280'}
                    strokeWidth={2}
                    dot={false}
                    connectNulls={true}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-700/50">
                  <tr>
                    <th className="px-4 py-2 text-left text-gray-300">Timestamp</th>
                    {exchanges.map(exchange => (
                      <th key={exchange} className="px-4 py-2 text-center text-gray-300">
                        {exchange}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {historicalData.map((item, index) => (
                    <tr key={index} className="hover:bg-gray-700/30">
                      <td className="px-4 py-2 text-gray-400">{item.timestamp}</td>
                      {exchanges.map(exchange => {
                        const value = item[exchange];
                        return (
                          <td
                            key={exchange}
                            className={clsx(
                              'px-4 py-2 text-center',
                              value !== null && value > 0 ? 'text-green-400' :
                              value !== null && value < 0 ? 'text-red-400' :
                              'text-gray-500'
                            )}
                          >
                            {value !== null ? `${(value as number).toFixed(4)}%` : '-'}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Summary Stats */}
        <div className="px-6 py-3 border-t border-gray-700 grid grid-cols-2 md:grid-cols-5 gap-4">
          {exchanges.map(exchange => {
            const values = historicalData
              .map(d => d[exchange])
              .filter(v => v !== null) as number[];
            
            if (values.length === 0) return null;
            
            const avg = values.reduce((a, b) => a + b, 0) / values.length;
            const min = Math.min(...values);
            const max = Math.max(...values);
            
            return (
              <div key={exchange} className="text-xs">
                <div className="font-medium text-gray-300">{exchange}</div>
                <div className="text-gray-400">
                  Avg: <span className={avg > 0 ? 'text-green-400' : 'text-red-400'}>
                    {avg.toFixed(4)}%
                  </span>
                </div>
                <div className="text-gray-500">
                  {min.toFixed(4)}% / {max.toFixed(4)}%
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default HistoricalFundingView;