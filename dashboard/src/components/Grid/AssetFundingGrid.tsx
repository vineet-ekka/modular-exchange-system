import React, { useState, useEffect, Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import { fetchContractsByAsset, ContractDetails } from '../../services/api';

interface ExchangeRate {
  funding_rate: number | null;
  apr: number | null;
}

interface AssetGridData {
  asset: string;
  exchanges: Record<string, ExchangeRate>;
}

const AssetFundingGrid: React.FC = () => {
  const navigate = useNavigate();
  const [gridData, setGridData] = useState<AssetGridData[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState<string>('asset');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [exchanges, setExchanges] = useState<string[]>([]);
  const [expandedAssets, setExpandedAssets] = useState<Set<string>>(new Set());
  const [contractsData, setContractsData] = useState<Record<string, ContractDetails[]>>({});
  const [loadingContracts, setLoadingContracts] = useState<Set<string>>(new Set());

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

  // Toggle asset expansion and fetch contract details
  const toggleAssetExpansion = async (asset: string) => {
    if (expandedAssets.has(asset)) {
      // Collapse
      setExpandedAssets(prev => {
        const newSet = new Set(prev);
        newSet.delete(asset);
        return newSet;
      });
    } else {
      // Expand and fetch data if not cached
      if (!contractsData[asset]) {
        setLoadingContracts(prev => new Set(prev).add(asset));
        try {
          console.log(`Fetching contracts for asset: ${asset}`);
          const contracts = await fetchContractsByAsset(asset);
          console.log(`Received ${contracts?.length || 0} contracts for ${asset}:`, contracts);
          setContractsData(prev => ({
            ...prev,
            [asset]: contracts
          }));
        } catch (error) {
          console.error(`Error fetching contracts for ${asset}:`, error);
        } finally {
          setLoadingContracts(prev => {
            const newSet = new Set(prev);
            newSet.delete(asset);
            return newSet;
          });
        }
      }
      setExpandedAssets(prev => new Set(prev).add(asset));
    }
  };

  const formatRate = (rate: number | null) => {
    if (rate === null || rate === undefined) return '-';
    return `${(rate * 100).toFixed(4)}%`;
  };

  const getRateColor = (rate: number | null) => {
    if (rate === null || rate === undefined) return 'text-funding-neutral';
    if (rate > 0) return 'text-funding-positive';
    if (rate < 0) return 'text-funding-negative';
    return 'text-gray-400';
  };

  const getRateBgColor = (rate: number | null) => {
    if (rate === null || rate === undefined) return '';
    if (rate > 0.001) return 'bg-accent-green/5';
    if (rate < -0.001) return 'bg-accent-red/5';
    return '';
  };

  // Format open interest based on contract type
  const formatOpenInterest = (contract: ContractDetails) => {
    const oi = contract.open_interest;
    if (!oi) return '-';
    
    // For USDT/USDC contracts, show USD value (OI * mark price)
    if (contract.quote_asset === 'USDT' || contract.quote_asset === 'USDC') {
      const usdValue = oi * (contract.mark_price || 0);
      if (usdValue > 1000000000) {
        return `${(usdValue / 1000000000).toFixed(2)}B USD`;
      } else if (usdValue > 1000000) {
        return `${(usdValue / 1000000).toFixed(2)}M USD`;
      } else if (usdValue > 1000) {
        return `${(usdValue / 1000).toFixed(2)}K USD`;
      }
      return `${usdValue.toLocaleString()} USD`;
    }
    
    // For COIN-M contracts (USD_PERP), show USD value
    if (contract.symbol.includes('USD_PERP')) {
      return `${(oi / 1000000).toFixed(2)}M USD`;
    }
    
    // For all other contracts, show base asset quantity
    const baseAsset = contract.base_asset;
    if (oi > 1000000) {
      return `${(oi / 1000000).toFixed(2)}M ${baseAsset}`;
    } else if (oi > 1000) {
      return `${(oi / 1000).toFixed(2)}K ${baseAsset}`;
    }
    return `${oi.toLocaleString()} ${baseAsset}`;
  };

  // Format price with proper decimals
  const formatPrice = (price: number) => {
    if (!price) return '-';
    return `$${price.toLocaleString('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    })}`;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl p-8 shadow-lg border border-light-border">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="space-y-2">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-lg border border-light-border overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-light-border bg-light-bg-secondary">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold text-text-primary">
            Market Overview
          </h2>
          <div className="flex items-center space-x-4">
            <button
              onClick={() => window.location.reload()}
              className="px-3 py-1 bg-text-primary hover:bg-gray-800 text-white rounded text-sm transition-colors shadow-sm"
            >
              Refresh
            </button>
            <span className="text-sm text-text-secondary">
              {sortedData.length} assets on Binance
            </span>
            <input
              type="text"
              placeholder="Search assets..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="px-3 py-1 bg-white border border-light-border rounded text-sm text-text-primary focus:outline-none focus:border-accent-blue"
            />
          </div>
        </div>
      </div>

      {/* Grid Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th 
                onClick={() => handleSort('asset')}
                className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider cursor-pointer hover:bg-gray-100 sticky left-0 bg-gray-50 z-10"
              >
                Asset {sortColumn === 'asset' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              {exchanges.map(exchange => (
                <th
                  key={exchange}
                  onClick={() => handleSort(exchange)}
                  className="px-4 py-3 text-center text-xs font-medium text-text-secondary uppercase tracking-wider cursor-pointer hover:bg-gray-100 min-w-[100px]"
                >
                  {exchange}
                  {sortColumn === exchange && (
                    <span className="ml-1">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-light-border bg-white">
            {sortedData.map((item) => (
              <Fragment key={item.asset}>
                <tr
                  onClick={() => toggleAssetExpansion(item.asset)}
                  className="hover:bg-gray-50 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3 whitespace-nowrap sticky left-0 bg-white z-10 border-r border-light-border">
                    <div className="flex items-center space-x-2">
                      <span className="text-gray-400 text-xs">
                        {expandedAssets.has(item.asset) ? '▼' : '▶'}
                      </span>
                      <span className="text-sm font-medium text-text-primary">
                        {item.asset}
                      </span>
                    </div>
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
                {expandedAssets.has(item.asset) && (
                  <tr className="expand-animation">
                    <td colSpan={exchanges.length + 1} className="p-0">
                      <div className="bg-gray-50 border-t border-b border-gray-200">
                        {loadingContracts.has(item.asset) ? (
                          <div className="p-4 text-center">
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-accent-blue mx-auto"></div>
                            <p className="text-sm text-gray-500 mt-2">Loading contracts...</p>
                          </div>
                        ) : contractsData[item.asset] && contractsData[item.asset].length > 0 ? (
                          <div className="p-4 overflow-x-auto">
                            <table className="w-full text-xs">
                              <thead className="bg-gray-100">
                                <tr>
                                  <th className="px-3 py-2 text-left font-medium text-gray-700">Contract Name</th>
                                  <th className="px-3 py-2 text-left font-medium text-gray-700">Exchange Name</th>
                                  <th className="px-3 py-2 text-left font-medium text-gray-700">Base Asset</th>
                                  <th className="px-3 py-2 text-left font-medium text-gray-700">Quote Asset</th>
                                  <th className="px-3 py-2 text-center font-medium text-gray-700">Funding Rate</th>
                                  <th className="px-3 py-2 text-center font-medium text-gray-700">APR</th>
                                  <th className="px-3 py-2 text-right font-medium text-gray-700">Open Interest</th>
                                  <th className="px-3 py-2 text-right font-medium text-gray-700">Mark Price</th>
                                  <th className="px-3 py-2 text-right font-medium text-gray-700">Index Price</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-gray-200">
                                {contractsData[item.asset].map((contract, idx) => (
                                  <tr key={`${contract.exchange}-${contract.symbol}`} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                    <td className="px-3 py-2 font-medium text-gray-900">{contract.symbol}</td>
                                    <td className="px-3 py-2 text-gray-700">{contract.exchange}</td>
                                    <td className="px-3 py-2 text-gray-700">{contract.base_asset}</td>
                                    <td className="px-3 py-2 text-gray-700">{contract.quote_asset}</td>
                                    <td className={clsx(
                                      'px-3 py-2 text-center font-medium',
                                      contract.funding_rate > 0 ? 'text-green-600' : contract.funding_rate < 0 ? 'text-red-600' : 'text-gray-500'
                                    )}>
                                      {formatRate(contract.funding_rate)}
                                    </td>
                                    <td className={clsx(
                                      'px-3 py-2 text-center font-medium',
                                      contract.apr > 0 ? 'text-green-600' : contract.apr < 0 ? 'text-red-600' : 'text-gray-500'
                                    )}>
                                      {contract.apr.toFixed(2)}%
                                    </td>
                                    <td className="px-3 py-2 text-right text-gray-700">
                                      {formatOpenInterest(contract)}
                                    </td>
                                    <td className="px-3 py-2 text-right text-gray-700">
                                      {formatPrice(contract.mark_price)}
                                    </td>
                                    <td className="px-3 py-2 text-right text-gray-700">
                                      {formatPrice(contract.index_price)}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                            <div className="mt-3 text-center">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  navigate(`/asset/${item.asset}`);
                                }}
                                className="text-sm text-blue-500 hover:text-blue-700 underline"
                              >
                                View History
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="p-4 text-center text-gray-500">
                            No contracts found for {item.asset}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="px-6 py-3 border-t border-light-border bg-light-bg-secondary flex items-center justify-between text-xs">
        <div className="flex items-center space-x-4">
          <span className="text-text-secondary font-medium">Funding:</span>
          <span className="text-funding-positive">● Positive (Long pays Short)</span>
          <span className="text-funding-negative">● Negative (Short pays Long)</span>
          <span className="text-funding-neutral">● No Data</span>
        </div>
        <div className="text-text-muted">
          Click arrow to expand contracts
        </div>
      </div>
    </div>
  );
};

export default AssetFundingGrid;