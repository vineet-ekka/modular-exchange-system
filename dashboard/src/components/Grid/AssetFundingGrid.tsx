import React, { useState, useEffect } from 'react';
import clsx from 'clsx';

interface ExchangeRate {
  funding_rate: number | null;
  apr: number | null;
}

interface AssetGridData {
  asset: string;
  exchanges: Record<string, ExchangeRate>;
}

interface AssetFundingGridProps {
  onAssetClick?: (asset: string) => void;
}

const AssetFundingGrid: React.FC<AssetFundingGridProps> = ({ onAssetClick }) => {
  const [gridData, setGridData] = useState<AssetGridData[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState<string>('asset');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [exchanges, setExchanges] = useState<string[]>([]);

  // Fetch grid data
  useEffect(() => {
    const fetchGridData = async () => {
      setLoading(true);
      try {
        const response = await fetch('http://localhost:8000/api/funding-rates-grid');
        const result = await response.json();
        
        console.log('Fetched grid data:', result); // Debug log
        
        if (result.data && result.data.length > 0) {
          setGridData(result.data);
          console.log('Set grid data with', result.data.length, 'assets'); // Debug log
          
          // Extract unique exchanges
          const uniqueExchanges = new Set<string>();
          result.data.forEach((item: AssetGridData) => {
            Object.keys(item.exchanges).forEach(exchange => {
              uniqueExchanges.add(exchange);
            });
          });
          const exchangeList = Array.from(uniqueExchanges).sort();
          setExchanges(exchangeList);
          console.log('Found exchanges:', exchangeList); // Debug log
        } else {
          console.log('No data received from API');
        }
      } catch (error) {
        console.error('Error fetching grid data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchGridData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchGridData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Filter data based on search
  const filteredData = gridData.filter(item =>
    item.asset.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Sort data
  const sortedData = [...filteredData].sort((a, b) => {
    let aVal: any = a.asset;
    let bVal: any = b.asset;

    if (sortColumn !== 'asset') {
      // Sorting by exchange column
      aVal = a.exchanges[sortColumn]?.funding_rate ?? -999;
      bVal = b.exchanges[sortColumn]?.funding_rate ?? -999;
    }

    if (typeof aVal === 'string') {
      return sortDirection === 'asc' 
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    } else {
      return sortDirection === 'asc'
        ? aVal - bVal
        : bVal - aVal;
    }
  });

  const handleSort = (column: string) => {
    if (column === sortColumn) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  const formatRate = (rate: number | null) => {
    if (rate === null || rate === undefined) return '-';
    return `${(rate * 100).toFixed(4)}%`;
  };

  const getRateColor = (rate: number | null) => {
    if (rate === null || rate === undefined) return 'text-gray-500';
    if (rate > 0) return 'text-green-400';
    if (rate < 0) return 'text-red-400';
    return 'text-gray-400';
  };

  const getRateBgColor = (rate: number | null) => {
    if (rate === null || rate === undefined) return '';
    if (rate > 0.001) return 'bg-green-900/20';
    if (rate < -0.001) return 'bg-red-900/20';
    return '';
  };

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-xl p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-700 rounded w-1/4"></div>
          <div className="h-4 bg-gray-700 rounded w-full"></div>
          <div className="space-y-2">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-xl shadow-xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-700">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-100">
            Binance Funding Rates
          </h2>
          <div className="flex items-center space-x-4">
            <button
              onClick={() => window.location.reload()}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm transition-colors"
            >
              Refresh
            </button>
            <span className="text-sm text-gray-400">
              {sortedData.length} assets on Binance
            </span>
            <input
              type="text"
              placeholder="Search assets..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="px-3 py-1 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Grid Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-700/50">
            <tr>
              <th 
                onClick={() => handleSort('asset')}
                className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-700/70 sticky left-0 bg-gray-700/50 z-10"
              >
                Asset {sortColumn === 'asset' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              {exchanges.map(exchange => (
                <th
                  key={exchange}
                  onClick={() => handleSort(exchange)}
                  className="px-4 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-700/70 min-w-[100px]"
                >
                  {exchange}
                  {sortColumn === exchange && (
                    <span className="ml-1">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {sortedData.map((item) => (
              <tr
                key={item.asset}
                onClick={() => onAssetClick?.(item.asset)}
                className="hover:bg-gray-700/30 transition-colors cursor-pointer"
              >
                <td className="px-4 py-3 whitespace-nowrap sticky left-0 bg-gray-800 z-10">
                  <span className="text-sm font-medium text-gray-200">
                    {item.asset}
                  </span>
                </td>
                {exchanges.map(exchange => {
                  const rate = item.exchanges[exchange]?.funding_rate ?? null;
                  return (
                    <td
                      key={exchange}
                      className={clsx(
                        'px-4 py-3 text-center whitespace-nowrap text-sm',
                        getRateBgColor(rate)
                      )}
                    >
                      <span className={getRateColor(rate)}>
                        {formatRate(rate)}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="px-6 py-3 border-t border-gray-700 flex items-center justify-between text-xs">
        <div className="flex items-center space-x-4">
          <span className="text-gray-400">Color Legend:</span>
          <span className="text-green-400">● Positive (Long pays Short)</span>
          <span className="text-red-400">● Negative (Short pays Long)</span>
          <span className="text-gray-500">● No Data</span>
        </div>
        <div className="text-gray-400">
          Click any asset row to view historical charts
        </div>
      </div>
    </div>
  );
};

export default AssetFundingGrid;