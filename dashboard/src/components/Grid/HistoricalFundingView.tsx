import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart
} from 'recharts';
import clsx from 'clsx';
import LiveFundingTicker from '../Ticker/LiveFundingTicker';
import FundingCountdown from '../Ticker/FundingCountdown';

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


interface HistoricalFundingViewProps {
  asset: string;
  onUpdate?: () => void;
}

// Define colors for different contracts - expanded for multiple exchanges
const CONTRACT_COLORS: Record<string, string> = {
  // Binance contracts
  'BTCUSDT': '#FFA726',      // Orange for USDT
  'BTCUSDC': '#42A5F5',      // Blue for USDC
  'BTCUSD_PERP': '#AB47BC',  // Purple for USD perpetual
  'ETHUSDT': '#66BB6A',      // Green for ETH USDT
  'ETHUSDC': '#26C6DA',      // Cyan for ETH USDC
  
  // Will be expanded for other exchanges
  'DEFAULT': '#9E9E9E'       // Gray for others
};

// Helper to get color for a contract
const getContractColor = (symbol: string): string => {
  // Check for exact match first
  if (CONTRACT_COLORS[symbol]) {
    return CONTRACT_COLORS[symbol];
  }
  
  // Check for pattern matches
  if (symbol.endsWith('USDT')) return '#FFA726';
  if (symbol.endsWith('USDC')) return '#42A5F5';
  if (symbol.endsWith('USD_PERP') || symbol.endsWith('USD')) return '#AB47BC';
  
  return CONTRACT_COLORS['DEFAULT'];
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
  const [timeRange, setTimeRange] = useState(7); // days
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

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
      const contractsResponse = await fetch(`http://localhost:8000/api/funding-rates?base_asset=${asset}&limit=100`);
      
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
            timestamp: new Date(item.timestamp).toLocaleString('en-US', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
              timeZone: 'UTC',
              timeZoneName: 'short'
            }),
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
        
        // Set combined data to just funding data (OI history removed)
        setCombinedData(processedFundingData);
          
          
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

  // Debug logging for rendering
  useEffect(() => {
    console.log('State Update:', {
      selectedContract: selectedContract
    });
  }, [selectedContract]);

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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <LiveFundingTicker asset={asset} selectedContract={selectedContract} />
            <FundingCountdown asset={asset} selectedContract={selectedContract} />
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

            {/* Time Range Selector */}
            <div className="flex space-x-2">
              {[1, 7, 30].map(days => (
                <button
                  key={days}
                  onClick={() => setTimeRange(days)}
                  className={clsx(
                    'px-3 py-1 rounded text-sm',
                    timeRange === days
                      ? 'bg-text-primary text-white'
                      : 'bg-white text-text-secondary hover:bg-gray-100 border border-light-border'
                  )}
                >
                  {days}D
                </button>
              ))}
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

        {/* Chart and Table Content - Both Visible */}
        <div className="bg-white">
          {/* Chart Section */}
          <div className="p-6 border-b border-light-border">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-700">APR Chart</h3>
              <span className="text-xs text-gray-500">All times in UTC</span>
            </div>
            {!selectedContract ? (
              <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
                <p className="text-gray-500">Please select a contract to display the chart</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={400}>
                <ComposedChart data={combinedData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis 
                    dataKey="timestamp" 
                    stroke="#9CA3AF"
                    tick={{ fontSize: 12, fill: '#6B7280' }}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis 
                    yAxisId="funding"
                    stroke="#9CA3AF"
                    tick={{ fontSize: 12, fill: '#6B7280' }}
                    label={{ 
                      value: 'APR (%)', 
                      angle: -90, 
                      position: 'insideLeft',
                      style: { fill: '#6b7280' }
                    }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#FFFFFF', 
                      border: '1px solid #E5E7EB',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                    }}
                    labelStyle={{ color: '#111827' }}
                    content={(props) => {
                      const { active, payload, label } = props;
                      if (!active || !payload) return null;
                      
                      const dataPoint = payload[0]?.payload;
                      
                      // Custom tooltip showing selected contract values
                      return (
                        <div className="bg-white p-3 rounded-lg border border-gray-200 shadow-lg">
                          <p className="font-semibold text-gray-800 mb-2">{label}</p>
                          {selectedContract && (() => {
                            const aprValue = dataPoint?.[`${selectedContract}_apr`];
                            const color = getContractColor(selectedContract);
                            
                            return (
                              <div className="flex items-center justify-between gap-4 py-1">
                                <span className="flex items-center gap-2">
                                  <span 
                                    className="w-3 h-0.5" 
                                    style={{ backgroundColor: color }}
                                  />
                                  <span className="text-sm text-gray-600">{selectedContract}:</span>
                                </span>
                                <span className="text-sm font-medium">
                                  {aprValue !== null && aprValue !== undefined 
                                    ? `${aprValue.toFixed(2)}% APR` 
                                    : 'N/A'}
                                </span>
                              </div>
                            );
                          })()}
                        </div>
                      );
                    }}
                  />
                  <Legend 
                    wrapperStyle={{ paddingTop: '20px' }}
                    iconType="line"
                  />
                  
                  {/* APR Line for selected contract */}
                  {selectedContract && (
                    <Line
                      key={selectedContract}
                      yAxisId="funding"
                      type="monotone"
                      dataKey={`${selectedContract}_apr`}
                      stroke={getContractColor(selectedContract)}
                      strokeWidth={2}
                      dot={false}
                      connectNulls={true}
                      name={selectedContract}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>
          
          {/* Table Section */}
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-700 mb-4">APR History</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-text-secondary font-medium">Timestamp (UTC)</th>
                    {selectedContract && (
                      <th className="px-4 py-2 text-center text-text-secondary font-medium">
                        {selectedContract} (APR %)
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-light-border">
                  {historicalData.map((item, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-text-secondary">{item.timestamp}</td>
                      {selectedContract && (() => {
                        const aprValue = item[`${selectedContract}_apr`];
                        return (
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
                        );
                      })()}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Summary Statistics */}
        <div className="px-6 py-4 border-t border-light-border bg-gray-50">
          <div className="flex justify-center text-sm">
            {selectedContract && (() => {
              const contractData = historicalData
                .map(d => d[`${selectedContract}_apr`])
                .filter(v => v !== null && v !== undefined && typeof v === 'number') as number[];
              
              if (contractData.length === 0) return null;
              
              const avg = contractData.reduce((a, b) => a + b, 0) / contractData.length;
              const min = contractData.length > 0 ? Math.min(...contractData) : 0;
              const max = contractData.length > 0 ? Math.max(...contractData) : 0;
              
              return (
                <div className="bg-white p-4 rounded border border-gray-200 max-w-md">
                  <div className="flex items-center space-x-2 mb-3">
                    <span 
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: getContractColor(selectedContract) }}
                    />
                    <span className="font-medium text-gray-700">{selectedContract} Statistics</span>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Avg:</span>
                      <span className={clsx(
                        'ml-1 font-medium',
                        avg > 0 ? 'text-green-600' : avg < 0 ? 'text-red-600' : 'text-gray-600'
                      )}>
                        {!isNaN(avg) && isFinite(avg) ? avg.toFixed(2) : '0.00'}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Min:</span>
                      <span className={clsx(
                        'ml-1 font-medium',
                        min > 0 ? 'text-green-600' : min < 0 ? 'text-red-600' : 'text-gray-600'
                      )}>
                        {!isNaN(min) && isFinite(min) ? min.toFixed(2) : '0.00'}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Max:</span>
                      <span className={clsx(
                        'ml-1 font-medium',
                        max > 0 ? 'text-green-600' : max < 0 ? 'text-red-600' : 'text-gray-600'
                      )}>
                        {!isNaN(max) && isFinite(max) ? max.toFixed(2) : '0.00'}%
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