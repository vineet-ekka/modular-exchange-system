import React, { useState, useEffect } from 'react';
import {
  fetchContractArbitrageOpportunities,
  ContractArbitrageOpportunity,
  ContractArbitrageResponse
} from '../services/arbitrage';

const ArbitrageOpportunities: React.FC = () => {
  const [data, setData] = useState<ContractArbitrageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [minSpread, setMinSpread] = useState(0.0005); // 0.05% default
  const [topN, setTopN] = useState(20);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await fetchContractArbitrageOpportunities(minSpread, topN);
      setData(response);
      setError(null);
    } catch (err) {
      setError('Failed to fetch contract arbitrage opportunities');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    if (autoRefresh) {
      const interval = setInterval(fetchData, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [minSpread, topN, autoRefresh]);

  const formatPercentage = (value: number) => {
    return `${value.toFixed(3)}%`;
  };

  const formatAPR = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const formatZScore = (value?: number | null) => {
    if (value === null || value === undefined) return '-';
    const formatted = value.toFixed(1);
    return value > 0 ? `+${formatted}` : formatted;
  };

  const getZScoreClass = (value?: number | null) => {
    if (value === null || value === undefined) return 'text-gray-400';
    const absValue = Math.abs(value);
    if (absValue > 3) return 'text-purple-600 font-bold'; // Extreme
    if (absValue > 2) return 'text-blue-600 font-semibold'; // Significant
    if (absValue > 1.5) return 'text-blue-500'; // Notable
    return 'text-gray-600'; // Normal
  };

  const getColorClass = (value: number) => {
    if (value > 0.5) return 'text-green-600 font-semibold';
    if (value > 0.3) return 'text-green-500';
    if (value > 0.1) return 'text-gray-700';
    return 'text-gray-400';
  };

  if (loading && !data) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading arbitrage opportunities...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-red-500">{error}</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header and Controls */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">
          Contract-Level Arbitrage Opportunities
          <span className="ml-2 text-sm font-normal text-green-600">(V2 - Accurate Z-Scores)</span>
        </h2>

        <div className="flex gap-4 items-center mb-4">
          <div>
            <label className="text-sm text-gray-600 mr-2">Min Spread:</label>
            <select
              className="border rounded px-2 py-1"
              value={minSpread}
              onChange={(e) => setMinSpread(parseFloat(e.target.value))}
            >
              <option value={0.0001}>0.01%</option>
              <option value={0.0005}>0.05%</option>
              <option value={0.001}>0.10%</option>
              <option value={0.002}>0.20%</option>
              <option value={0.005}>0.50%</option>
            </select>
          </div>

          <div>
            <label className="text-sm text-gray-600 mr-2">Top N:</label>
            <select
              className="border rounded px-2 py-1"
              value={topN}
              onChange={(e) => setTopN(parseInt(e.target.value))}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="autoRefresh"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="mr-2"
            />
            <label htmlFor="autoRefresh" className="text-sm text-gray-600">
              Auto-refresh (30s)
            </label>
          </div>

          <button
            onClick={fetchData}
            className="px-4 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Refresh Now
          </button>
        </div>

        {/* Statistics */}
        {data?.statistics && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-4">
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-xs text-gray-500">Total Opportunities</div>
              <div className="text-xl font-semibold">{data.statistics.total_opportunities}</div>
            </div>
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-xs text-gray-500">Max Spread</div>
              <div className="text-xl font-semibold">{formatPercentage(data.statistics.max_spread)}</div>
            </div>
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-xs text-gray-500">Max APR Spread</div>
              <div className="text-xl font-semibold">{formatAPR(data.statistics.max_apr_spread)}</div>
            </div>
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-xs text-gray-500">Avg Spread</div>
              <div className="text-xl font-semibold">{formatPercentage(data.statistics.average_spread)}</div>
            </div>
            <div className="bg-blue-50 p-3 rounded">
              <div className="text-xs text-blue-600">Significant (|Z|{'>'} 2)</div>
              <div className="text-xl font-semibold text-blue-700">{data.statistics.significant_count || 0}</div>
            </div>
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-xs text-gray-500">Contracts Analyzed</div>
              <div className="text-xl font-semibold">{data.statistics.contracts_analyzed || 0}</div>
            </div>
          </div>
        )}
      </div>

      {/* Opportunities Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Asset</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Long Contract</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Short Contract</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Long Rate</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Short Rate</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Rate Spread</th>
              <th className="px-2 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Long Z</th>
              <th className="px-2 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Short Z</th>
              <th className="px-2 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">L %ile</th>
              <th className="px-2 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">S %ile</th>
              <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Intervals</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">APR Spread</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {data?.opportunities.length === 0 ? (
              <tr>
                <td colSpan={12} className="px-4 py-8 text-center text-gray-500">
                  No contract-level arbitrage opportunities found with current filters
                </td>
              </tr>
            ) : (
              data?.opportunities.map((opp, index) => (
                <tr key={`${opp.asset}-${opp.long_contract}-${opp.short_contract}-${index}`} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm font-medium text-gray-900">{opp.asset}</td>
                  <td className="px-4 py-2 text-sm text-gray-700">
                    <div>
                      <span className="font-medium">{opp.long_contract}</span>
                      <span className="ml-1 text-xs text-gray-500">({opp.long_exchange})</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-sm text-gray-700">
                    <div>
                      <span className="font-medium">{opp.short_contract}</span>
                      <span className="ml-1 text-xs text-gray-500">({opp.short_exchange})</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-sm text-right text-gray-600">
                    {formatPercentage(opp.long_rate * 100)}
                  </td>
                  <td className="px-4 py-2 text-sm text-right text-gray-600">
                    {formatPercentage(opp.short_rate * 100)}
                  </td>
                  <td className={`px-4 py-2 text-sm text-right font-medium ${getColorClass(opp.rate_spread_pct)}`}>
                    {formatPercentage(opp.rate_spread_pct)}
                  </td>
                  <td className={`px-2 py-2 text-xs text-right ${getZScoreClass(opp.long_zscore)}`}>
                    {formatZScore(opp.long_zscore)}
                  </td>
                  <td className={`px-2 py-2 text-xs text-right ${getZScoreClass(opp.short_zscore)}`}>
                    {formatZScore(opp.short_zscore)}
                  </td>
                  <td className="px-2 py-2 text-xs text-right">
                    {opp.long_percentile ? (
                      <span className={opp.long_percentile > 95 || opp.long_percentile < 5 ? 'text-purple-600 font-semibold' :
                                      opp.long_percentile > 90 || opp.long_percentile < 10 ? 'text-blue-600' :
                                      opp.long_percentile > 80 || opp.long_percentile < 20 ? 'text-blue-500' : 'text-gray-600'}>
                        {opp.long_percentile.toFixed(0)}%
                      </span>
                    ) : '-'}
                  </td>
                  <td className="px-2 py-2 text-xs text-right">
                    {opp.short_percentile ? (
                      <span className={opp.short_percentile > 95 || opp.short_percentile < 5 ? 'text-purple-600 font-semibold' :
                                      opp.short_percentile > 90 || opp.short_percentile < 10 ? 'text-blue-600' :
                                      opp.short_percentile > 80 || opp.short_percentile < 20 ? 'text-blue-500' : 'text-gray-600'}>
                        {opp.short_percentile.toFixed(0)}%
                      </span>
                    ) : '-'}
                  </td>
                  <td className="px-4 py-2 text-sm text-center text-gray-500">
                    <span className="text-xs">{opp.long_interval_hours}h/{opp.short_interval_hours}h</span>
                  </td>
                  <td className={`px-4 py-2 text-sm text-right ${opp.apr_spread ? getColorClass(opp.apr_spread / 100) : ''}`}>
                    {opp.apr_spread ? formatAPR(opp.apr_spread) : '-'}
                    {opp.is_significant && (
                      <span className="ml-1 text-xs px-1 py-0.5 bg-blue-100 text-blue-800 rounded">
                        Sig
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="mt-4 text-xs text-gray-500">
        <p className="font-semibold mb-1">Contract-Specific Arbitrage (V2):</p>
        <p>* Long Contract = Specific contract to buy/go long (lower funding rate)</p>
        <p>* Short Contract = Specific contract to sell/go short (higher funding rate)</p>
        <p>* Long/Short Z = Z-scores for the SPECIFIC contracts shown</p>
        <p>* L/S %ile = Percentile ranks for each specific contract</p>
        <p>* Rate Spread = Difference in funding rates between these exact contracts</p>
        <p>* Intervals = Funding interval hours for each contract</p>
        <p>* APR Spread = Annualized return based on actual funding intervals</p>
        <p>* "Sig" = At least one contract has |Z-score| {'>'} 2</p>
      </div>
    </div>
  );
};

export default ArbitrageOpportunities;