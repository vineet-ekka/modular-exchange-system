import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
// Chart components removed - table view only
import clsx from 'clsx';
import LiveFundingTicker from '../Ticker/LiveFundingTicker';
import ModernPagination from '../Modern/ModernPagination';
// FundingChartTooltip removed - no longer using charts
import { calculateContractStats } from '../../utils/fundingChartUtils';
import type { ProcessedFundingData } from '../../types/fundingChart';

interface HistoricalDataPoint {
  timestamp: string;
  rawTimestamp?: string;
  [key: string]: string | number | null | undefined;
}

interface ChartDataPoint {
  timestamp: string;
  rawTimestamp: string;
  [key: string]: string | number | null;
}

// Smart time formatter - uses detailed format for tables
const formatChartTime = (timestamp: string): string => {
  const date = new Date(timestamp);

  // Consistent month names (3-letter abbreviations)
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const month = monthNames[date.getUTCMonth()];
  const day = date.getUTCDate();
  const hours = date.getUTCHours();
  const minutes = date.getUTCMinutes();
  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours % 12 || 12;

  const timeString = minutes === 0
    ? `${displayHours} ${period}`
    : `${displayHours}:${minutes.toString().padStart(2, '0')} ${period}`;

  return `${month} ${day}, ${timeString}`;
}

interface HistoricalFundingViewProps {
  asset: string;
  onUpdate?: () => void;
}

// Dynamic color assignment for contracts based on patterns
const getContractColor = (symbol: string): string => {
  // Pattern-based color assignment
  if (symbol.endsWith('USDT')) return '#FFA726';      // Orange for USDT
  if (symbol.endsWith('USDC')) return '#42A5F5';      // Blue for USDC
  if (symbol.endsWith('USD_PERP') || symbol.endsWith('USD')) return '#AB47BC';  // Purple for USD perpetual
  if (symbol.startsWith('ETH')) return '#66BB6A';     // Green for ETH pairs
  if (symbol.startsWith('BTC')) return '#F7931A';     // Bitcoin orange
  if (symbol.startsWith('XBT')) return '#F7931A';     // KuCoin Bitcoin
  
  // Generate a consistent color based on symbol hash
  let hash = 0;
  for (let i = 0; i < symbol.length; i++) {
    hash = symbol.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 70%, 50%)`;
};



// Extract exchange name from contract symbol
const getExchangeFromContract = (contract: string): string => {
  // Parse exchange from contract format: "SYMBOL (Exchange)"
  const match = contract.match(/\(([^)]+)\)$/);
  if (match) {
    return match[1];
  }
  
  // Fallback: Check for common patterns based on actual contract names
  // KuCoin contracts start with XBT
  if (contract.startsWith('XBT')) return 'KuCoin';
  
  // Backpack contracts end with _PERP
  if (contract.endsWith('_PERP')) return 'Backpack';
  
  // Hyperliquid uses BTCUSD_PERP format
  if (contract === 'BTCUSD_PERP') return 'Hyperliquid';
  
  // Binance uses simple format like BTCUSDT, BTCUSDC
  if (contract === 'BTCUSDT' || contract === 'BTCUSDC' || contract === 'BTCBUSD') return 'Binance';
  
  // Default fallback
  return 'Exchange';
};

// Group contracts by exchange
const groupContractsByExchange = (contracts: string[]): Record<string, string[]> => {
  const grouped: Record<string, string[]> = {};
  
  contracts.forEach(contract => {
    const exchange = getExchangeFromContract(contract);
    if (!grouped[exchange]) {
      grouped[exchange] = [];
    }
    grouped[exchange].push(contract);
  });
  
  return grouped;
};

const HistoricalFundingView: React.FC<HistoricalFundingViewProps> = ({ asset, onUpdate }) => {
  const navigate = useNavigate();
  const [historicalData, setHistoricalData] = useState<HistoricalDataPoint[]>([]);
  const [combinedData, setCombinedData] = useState<ChartDataPoint[]>([]);
  const [allContracts, setAllContracts] = useState<Array<{symbol: string, exchange: string}>>([]);  // All available contracts with exchange info
  const [selectedContract, setSelectedContract] = useState<string>('');  // Single selected contract
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(30); // days
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [fundingInterval, setFundingInterval] = useState<number>(8);
  const [actualFundingTimes, setActualFundingTimes] = useState<string[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 25;

  // Handle clicks outside dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchHistoricalData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // First, fetch ALL available contracts for this asset
      const contractsResponse = await fetch(`http://localhost:8000/api/funding-rates?base_asset=${asset}&limit=2000`);
      
      if (contractsResponse.ok) {
        const contractsData = await contractsResponse.json();
        // Store contracts with their exchange info to handle duplicates
        const contractsList = contractsData.map((item: any) => ({
          symbol: item.symbol,
          exchange: item.exchange
        }));
        setAllContracts(contractsList);
      }
      
      // Fetch funding rates data
      const fundingResponse = await fetch(`http://localhost:8000/api/historical-funding-by-asset/${asset}?days=${timeRange}`);
      
      if (!fundingResponse.ok) {
        throw new Error(`Failed to fetch data: ${fundingResponse.status} ${fundingResponse.statusText}`);
      }
      
      const fundingResult = await fundingResponse.json();
        
      if (fundingResult.data) {
        // Process funding data - now handling contracts instead of exchanges
        const processedFundingData = fundingResult.data.map((item: HistoricalDataPoint) => {
          const point: ChartDataPoint = {
            timestamp: formatChartTime(item.timestamp),
            rawTimestamp: item.timestamp
          };
          
          // Store both funding rates and APR for each CONTRACT
          const contractList = fundingResult.contracts || fundingResult.exchanges || [];
          contractList.forEach((contract: string) => {
            const value = item[contract];
            const aprValue = item[`${contract}_apr`];
            point[contract] = value !== null ? (value as number) * 100 : null;
            point[`${contract}_apr`] = aprValue !== null && aprValue !== undefined ? aprValue : null;
          });
          
          return point;
        });
        
        setHistoricalData(processedFundingData);
        // Only update contracts if we didn't get them from the funding-rates endpoint
        if (allContracts.length === 0) {
          // Fallback to contracts from historical data
          const historicalContracts = fundingResult.contracts || fundingResult.exchanges || [];
          if (historicalContracts.length > 0) {
            // Convert string array to contract objects (assume they're from various exchanges)
            const contractsList = historicalContracts.map((symbol: string) => ({
              symbol: symbol,
              exchange: 'Multiple' // We don't know the exchange from historical data
            }));
            setAllContracts(contractsList);
          }
        }
        
        // Set default selected contract (first USDT contract or first available)
        // Always set the selected contract if we have contracts and none is selected
        if (allContracts.length > 0 || fundingResult.contracts?.length > 0) {
          const contractsToCheck = allContracts.length > 0 ? allContracts.map(c => c.symbol) : (fundingResult.contracts || []);
          setSelectedContract(prevContract => {
            if (prevContract && contractsToCheck.includes(prevContract)) {
              // Keep the current selection if it's still valid
              return prevContract;
            }
            // Otherwise select a new default
            const usdtContracts = contractsToCheck.filter((c: string) => c.includes('USDT'));
            if (usdtContracts.length > 0) {
              return usdtContracts[0];
            }
            return contractsToCheck[0] || '';
          });
        }
        
        // Use raw data directly for smooth line visualization
        setCombinedData(processedFundingData);
        
        // Extract funding interval from the first data point if available
        if (selectedContract && processedFundingData.length > 0) {
          // Try to determine funding interval from the data
          const interval = 8; // Default to 8 hours, can be extracted from metadata if available
          setFundingInterval(interval);
        }
          
          
      }
      
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Error fetching historical data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load historical data');
    } finally {
      setLoading(false);
    }
  }, [asset, timeRange]);

  useEffect(() => {
    if (asset) {
      fetchHistoricalData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asset, timeRange]); // Intentionally exclude fetchHistoricalData to prevent infinite loop

  // Separate effect for auto-refresh
  useEffect(() => {
    if (asset) {
      const refreshInterval = setInterval(() => {
        fetchHistoricalData();
      }, 30000);
      
      return () => clearInterval(refreshInterval);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asset]); // Only re-setup interval when asset changes

  // Update parent component when data changes - only on successful load
  useEffect(() => {
    if (onUpdate && !loading && historicalData.length > 0) {
      onUpdate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historicalData.length]); // Only trigger when data actually changes, not onUpdate or loading

  // Update combined data when selected contract or historical data changes
  useEffect(() => {
    if (historicalData.length > 0) {
      // Ensure rawTimestamp is always defined for ChartDataPoint type
      const chartData = historicalData.map(item => ({
        ...item,
        rawTimestamp: item.rawTimestamp || item.timestamp
      })) as ChartDataPoint[];
      setCombinedData(chartData);
      
      // Debug: Log the data to see what's being charted
      if (selectedContract && chartData.length > 0) {
        console.log('Chart data for', selectedContract, ':', {
          firstPoint: chartData[0][selectedContract],
          firstAPR: chartData[0][`${selectedContract}_apr`],
          dataKey: selectedContract,
          sample: chartData.slice(0, 3)
        });
      }
    }
  }, [selectedContract, historicalData]);

  const exportToCSV = () => {
    if (historicalData.length === 0 || !selectedContract) return;

    const headers = ['Timestamp', `${selectedContract} Funding Rate (%)`, `${selectedContract} APR (%)`];
    const rows = historicalData.map(item => {
      const row = [item.timestamp];
      const fundingValue = item[selectedContract];
      const aprValue = item[`${selectedContract}_apr`];
      row.push(fundingValue !== null && fundingValue !== undefined ? fundingValue.toString() : '');
      row.push(aprValue !== null && aprValue !== undefined ? aprValue.toString() : '');
      return row.join(',');
    });

    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${asset}_${selectedContract}_APR_${timeRange}d.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Handle contract selection
  const handleContractSelect = (contract: string) => {
    setSelectedContract(contract);
    setDropdownOpen(false);
    setSearchTerm('');
  };

  // Filter contracts based on search term
  const filteredContracts = allContracts.filter(contract =>
    contract.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
    contract.exchange.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Group contracts by exchange - now we have the exchange info directly
  const groupedContracts: Record<string, Array<{symbol: string, exchange: string}>> = {};
  filteredContracts.forEach(contract => {
    if (!groupedContracts[contract.exchange]) {
      groupedContracts[contract.exchange] = [];
    }
    groupedContracts[contract.exchange].push(contract);
  });

  // Pagination logic
  const totalPages = Math.ceil(historicalData.length / pageSize);
  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return historicalData.slice(startIndex, endIndex);
  }, [historicalData, currentPage, pageSize]);

  // Reset to page 1 when selectedContract changes
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedContract]);

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
                {asset} Historical Funding Rates & APR
              </h2>
              <p className="text-sm text-text-secondary mt-1">
                Showing {selectedContract || 'No contract selected'} - Total: {allContracts.length} contracts
              </p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 bg-text-primary text-white hover:bg-gray-800 rounded text-sm transition-colors"
            >
              Back to Dashboard
            </button>
          </div>
          
          {/* Live Ticker and Countdown Row */}
          <div className="mt-4">
            <LiveFundingTicker asset={asset} selectedContract={selectedContract} />
          </div>
        </div>

        {/* Controls */}
        <div className="px-6 py-3 border-b border-light-border bg-gray-50 flex justify-between items-center">
          <div className="flex items-center space-x-4">
            {/* Contract Selector Dropdown */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm flex items-center space-x-2 hover:bg-gray-50"
              >
                <span>{selectedContract || 'Select Contract'}</span>
                <svg className={`w-4 h-4 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              
              {dropdownOpen && (
                <div className="absolute z-50 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg">
                  <div className="p-3 border-b border-gray-200">
                    <span className="text-sm font-medium text-gray-700">Select Contract</span>
                    <input
                      type="text"
                      placeholder="Search contracts..."
                      value={searchTerm}
                      className="w-full px-2 py-1 mt-2 text-sm border border-gray-300 rounded"
                      onChange={(e) => setSearchTerm(e.target.value)}
                      autoFocus
                    />
                  </div>
                  
                  <div className="max-h-60 overflow-y-auto p-3">
                    {Object.keys(groupedContracts).length === 0 ? (
                      <div className="text-center text-gray-500 py-4">
                        No contracts found matching "{searchTerm}"
                      </div>
                    ) : (
                      Object.entries(groupedContracts).map(([exchange, contracts]) => (
                      <div key={exchange} className="mb-3">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="text-sm font-medium text-gray-700">{exchange}</span>
                          <span className="text-xs text-gray-500">({contracts.length})</span>
                        </div>
                        <div className="ml-4 space-y-1">
                          {contracts.map(contract => (
                            <button
                              key={`${contract.symbol}-${contract.exchange}`}
                              onClick={() => handleContractSelect(contract.symbol)}
                              className={`w-full flex items-center space-x-2 hover:bg-gray-50 p-2 rounded text-left ${
                                selectedContract === contract.symbol ? 'bg-blue-50 border-l-2 border-blue-500' : ''
                              }`}
                            >
                              <span className="text-sm text-gray-600">{contract.symbol}</span>
                              <span 
                                className="w-3 h-3 rounded-full ml-auto"
                                style={{ backgroundColor: getContractColor(contract.symbol) }}
                              />
                            </button>
                          ))}
                        </div>
                      </div>
                    )))}
                  </div>
                </div>
              )}
            </div>

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

        {/* Table Content Only */}
        <div className="bg-white">
          {/* Table Section */}
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-700 mb-4">Funding Rate History</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-text-secondary font-medium">Timestamp (UTC)</th>
                    {selectedContract && (
                      <>
                        <th className="px-4 py-2 text-center text-text-secondary font-medium">
                          {selectedContract} Funding Rate (%)
                        </th>
                        <th className="px-4 py-2 text-center text-text-secondary font-medium">
                          APR (%)
                        </th>
                      </>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-light-border">
                  {[...paginatedData].reverse().map((item, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-text-secondary">{item.timestamp}</td>
                      {selectedContract && (() => {
                        const fundingValue = item[selectedContract];
                        const aprValue = item[`${selectedContract}_apr`];
                        return (
                          <>
                            <td
                              className={clsx(
                                'px-4 py-2 text-center',
                                fundingValue !== null && fundingValue !== undefined && fundingValue > 0 ? 'text-funding-positive' :
                                fundingValue !== null && fundingValue !== undefined && fundingValue < 0 ? 'text-funding-negative' :
                                'text-funding-neutral'
                              )}
                            >
                              {fundingValue !== null && fundingValue !== undefined && !isNaN(fundingValue as number) ? `${(fundingValue as number).toFixed(4)}%` : '-'}
                            </td>
                            <td
                              className={clsx(
                                'px-4 py-2 text-center',
                                aprValue !== null && aprValue !== undefined && aprValue > 0 ? 'text-funding-positive' :
                                aprValue !== null && aprValue !== undefined && aprValue < 0 ? 'text-funding-negative' :
                                'text-funding-neutral'
                              )}
                            >
                              {aprValue !== null && aprValue !== undefined && !isNaN(aprValue as number) ? `${(aprValue as number).toFixed(2)}%` : '-'}
                            </td>
                          </>
                        );
                      })()}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Pagination - only show when there are multiple pages */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-light-border bg-white">
            <ModernPagination
              currentPage={currentPage}
              totalPages={totalPages}
              pageSize={pageSize}
              totalItems={historicalData.length}
              onPageChange={setCurrentPage}
            />
          </div>
        )}

        {/* Show results count when single page */}
        {totalPages === 1 && (
          <div className="px-6 py-4 border-t border-light-border bg-white">
            <div className="text-sm text-text-secondary text-center">
              Showing all {historicalData.length} results
            </div>
          </div>
        )}

        {/* Summary Statistics */}
        <div className="px-6 py-4 border-t border-light-border bg-gray-50">
          <div className="flex justify-center text-sm">
            {selectedContract && (() => {
              const stats = calculateContractStats(historicalData, selectedContract);
              
              if (stats.count === 0) return null;
              
              return (
                <div className="bg-white p-4 rounded border border-gray-200 max-w-md">
                  <div className="flex items-center space-x-2 mb-3">
                    <span 
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: getContractColor(selectedContract) }}
                    />
                    <span className="font-medium text-gray-700">
                      {selectedContract} Statistics [{fundingInterval}h interval]
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
              );
            })()}
          </div>
        </div>
    </div>
  );
};

export default HistoricalFundingView;