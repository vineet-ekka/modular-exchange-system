import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
// Chart components removed - table view only
import clsx from 'clsx';
import LiveFundingTicker from '../Ticker/LiveFundingTicker';

interface HistoricalDataPoint {
  timestamp: string;
  displayTime?: string;
  funding_rate: number | null;
  apr: number | null;
  mark_price?: number | null;
  open_interest?: number | null;
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
  const navigate = useNavigate();
  const [historicalData, setHistoricalData] = useState<HistoricalDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(7); // days
  const [error, setError] = useState<string | null>(null);
  const [fundingInterval, setFundingInterval] = useState<number>(8);
  const [baseAsset, setBaseAsset] = useState<string>('');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  
  const fetchHistoricalData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      let response;
      
      if (isContractView && exchange && symbol) {
        // Fetch single contract data
        response = await fetch(
          `http://localhost:8000/api/historical-funding-by-contract/${exchange}/${symbol}?days=${timeRange}`
        );
      } else if (asset) {
        // Fallback to asset-based view (old behavior)
        response = await fetch(
          `http://localhost:8000/api/historical-funding-by-asset/${asset}?days=${timeRange}`
        );
      } else {
        throw new Error('No asset or contract specified');
      }
      
      if (!response.ok) {
        throw new Error(`Failed to fetch data: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      
      if (isContractView) {
        // Contract-specific data - need to convert funding_rate to percentage
        const processedData = result.data?.map((item: any) => ({
          timestamp: item.timestamp,
          displayTime: new Date(item.timestamp).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZone: 'UTC'
          }),
          funding_rate: item.funding_rate !== null ? item.funding_rate * 100 : null, // Convert to percentage
          apr: item.apr || null,
          mark_price: item.mark_price || null,
          open_interest: item.open_interest || null
        })) || [];
        // Reverse the array to show oldest first for proper chart display
        setHistoricalData(processedData.reverse());
        setFundingInterval(result.funding_interval_hours || 8);
        setBaseAsset(result.base_asset || symbol || '');
      } else {
        // Asset-based data (old format) - extract first contract
        const contracts = result.contracts || [];
        if (contracts.length > 0) {
          const firstContract = contracts[0];
          const processedData = result.data?.map((item: any) => ({
            timestamp: item.timestamp,
            funding_rate: item[firstContract] ? item[firstContract] * 100 : null,
            apr: item[`${firstContract}_apr`] || null
          })) || [];
          setHistoricalData(processedData);
          setBaseAsset(asset || '');
        }
      }
      
      // Call onUpdate after successful data fetch
      if (onUpdate) {
        onUpdate();
      }
      
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Error fetching historical data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load historical data');
    } finally {
      setLoading(false);
    }
  }, [asset, exchange, symbol, isContractView, timeRange]); // Removed onUpdate from dependencies
  
  useEffect(() => {
    if ((isContractView && exchange && symbol) || asset) {
      fetchHistoricalData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asset, exchange, symbol, isContractView, timeRange]); // Use specific dependencies instead
  
  // Auto-refresh every 30 seconds
  useEffect(() => {
    if ((isContractView && exchange && symbol) || asset) {
      const interval = setInterval(() => {
        fetchHistoricalData();
      }, 30000);
      
      return () => clearInterval(interval);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asset, exchange, symbol, isContractView]); // Only re-setup when route changes
  
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
  
  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-light-border bg-light-bg-secondary">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-2xl font-semibold text-text-primary">
              {isContractView 
                ? `${symbol} Historical Funding Rates`
                : `${baseAsset || asset} Historical Funding Rates`
              }
            </h2>
            <p className="text-sm text-text-secondary mt-1">
              {isContractView 
                ? `Exchange: ${exchange} | Funding Interval: ${fundingInterval}h | Base Asset: ${baseAsset}`
                : `Showing consolidated data across all contracts`
              }
            </p>
          </div>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-text-primary text-white hover:bg-gray-800 rounded text-sm transition-colors"
          >
            Back to Dashboard
          </button>
        </div>
        
        {/* Live Ticker and Countdown */}
        {isContractView && (
          <div className="mt-4">
            <LiveFundingTicker asset={baseAsset} selectedContract={symbol} />
          </div>
        )}
      </div>
      
      {/* Controls */}
      <div className="px-6 py-3 border-b border-light-border bg-gray-50 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <div className="text-xs text-gray-500">
            Last updated: {lastUpdate.toLocaleTimeString('en-US', { timeZone: 'UTC', timeZoneName: 'short' })}
          </div>
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