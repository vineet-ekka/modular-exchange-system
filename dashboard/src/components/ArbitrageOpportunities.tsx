import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  fetchContractArbitrageOpportunities,
  ContractArbitrageOpportunity,
  ContractArbitrageResponse
} from '../services/arbitrage';
import { ModernCard, ModernButton, ModernSelect, ModernToggle, ModernTable, ModernBadge } from './Modern';
import clsx from 'clsx';

const ArbitrageOpportunities: React.FC = () => {
  const [data, setData] = useState<ContractArbitrageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [minSpread, setMinSpread] = useState(0.0005);
  const [topN, setTopN] = useState(20);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchData = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();

    try {
      setLoading(true);
      const response = await fetchContractArbitrageOpportunities(minSpread, topN);

      if (!abortControllerRef.current.signal.aborted) {
        setData(response);
        setError(null);
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setError('Failed to fetch arbitrage opportunities');
        console.error(err);
      }
    } finally {
      setLoading(false);
    }
  }, [minSpread, topN]);

  // Initial fetch and fetch on filter changes
  useEffect(() => {
    fetchData();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [minSpread, topN]);

  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (autoRefresh) {
      intervalRef.current = setInterval(() => {
        fetchData();
      }, 30000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, fetchData]);

  const formatPercentage = (value?: number | null) => {
    if (value === null || value === undefined) return '-';
    const percentage = value * 100;
    return `${percentage >= 0 ? '+' : ''}${percentage.toFixed(3)}%`;
  };

  // For values that are already in percentage format (not decimals)
  const formatPercentageValue = (value?: number | null) => {
    if (value === null || value === undefined) return '-';
    return `${value >= 0 ? '+' : ''}${value.toFixed(3)}%`;
  };

  const formatAPR = (value?: number | null) => {
    if (value === null || value === undefined) return '-';
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatOpenInterest = (value?: number | null) => {
    if (value === null || value === undefined) return '-';
    const absValue = Math.abs(value);

    if (absValue >= 1e9) {
      return `$${(value / 1e9).toFixed(2)}B`;
    } else if (absValue >= 1e6) {
      return `$${(value / 1e6).toFixed(1)}M`;
    } else if (absValue >= 1e3) {
      return `$${(value / 1e3).toFixed(0)}K`;
    } else {
      return `$${value.toFixed(0)}`;
    }
  };

  const getZScoreBadge = (zScore?: number | null) => {
    if (zScore === null || zScore === undefined) return null;

    const absZ = Math.abs(zScore);
    let variant: 'danger' | 'warning' | 'info' | 'neutral' = 'neutral';

    if (absZ >= 3) variant = 'danger';
    else if (absZ >= 2) variant = 'warning';
    else if (absZ >= 1) variant = 'info';

    return (
      <ModernBadge variant={variant} size="sm">
        Z: {zScore.toFixed(2)}
      </ModernBadge>
    );
  };

  if (loading && !data) {
    return (
      <ModernCard variant="default" padding="xl">
        <div className="flex flex-col items-center justify-center py-8">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-text-secondary">Loading arbitrage opportunities...</p>
        </div>
      </ModernCard>
    );
  }

  if (error) {
    return (
      <ModernCard variant="default" padding="xl">
        <div className="text-center py-8">
          <p className="text-danger text-lg font-medium">{error}</p>
          <ModernButton
            variant="primary"
            onClick={fetchData}
            className="mt-4"
          >
            Retry
          </ModernButton>
        </div>
      </ModernCard>
    );
  }

  const columns = [
    {
      key: 'asset',
      header: 'Asset',
      accessor: (row: ContractArbitrageOpportunity) => (
        <span className="font-bold text-text-primary">{row.asset}</span>
      ),
      align: 'left' as const,
    },
    {
      key: 'long',
      header: 'Long Position',
      accessor: (row: ContractArbitrageOpportunity) => (
        <div>
          <div className="font-medium">{row.long_contract}</div>
          <div className="text-xs text-text-tertiary">{row.long_exchange}</div>
          <div className={clsx('text-sm font-mono', row.long_rate < 0 ? 'text-success' : 'text-danger')}>
            {formatPercentage(row.long_rate)}
          </div>
        </div>
      ),
      align: 'left' as const,
    },
    {
      key: 'short',
      header: 'Short Position',
      accessor: (row: ContractArbitrageOpportunity) => (
        <div>
          <div className="font-medium">{row.short_contract}</div>
          <div className="text-xs text-text-tertiary">{row.short_exchange}</div>
          <div className={clsx('text-sm font-mono', row.short_rate > 0 ? 'text-success' : 'text-danger')}>
            {formatPercentage(row.short_rate)}
          </div>
        </div>
      ),
      align: 'left' as const,
    },
    {
      key: 'spread',
      header: 'Spread',
      accessor: (row: ContractArbitrageOpportunity) => (
        <div className="text-center">
          <div className="text-lg font-bold text-primary">
            {formatPercentage(row.rate_spread)}
          </div>
          <div className="text-xs text-text-secondary">
            APR: {formatAPR(row.apr_spread)}
          </div>
        </div>
      ),
      align: 'center' as const,
    },
    {
      key: 'intervals',
      header: 'Intervals',
      accessor: (row: ContractArbitrageOpportunity) => (
        <div className="text-center">
          <div className="text-sm">
            {row.long_interval_hours}h / {row.short_interval_hours}h
          </div>
        </div>
      ),
      align: 'center' as const,
    },
    {
      key: 'zscores',
      header: 'Z-Scores',
      accessor: (row: ContractArbitrageOpportunity) => (
        <div className="flex gap-1 justify-center">
          {getZScoreBadge(row.long_zscore)}
          {getZScoreBadge(row.short_zscore)}
        </div>
      ),
      align: 'center' as const,
    },
    {
      key: 'openInterest',
      header: 'Open Interest',
      accessor: (row: ContractArbitrageOpportunity) => (
        <div className="text-right">
          <div className="text-sm">{formatOpenInterest(row.long_open_interest)}</div>
          <div className="text-sm">{formatOpenInterest(row.short_open_interest)}</div>
        </div>
      ),
      align: 'right' as const,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Controls */}
      <ModernCard padding="lg">
        <div className="flex flex-wrap gap-4 items-end">
          <ModernSelect
            label="Minimum Spread"
            value={minSpread}
            onChange={(value) => setMinSpread(Number(value))}
            options={[
              { value: 0.0001, label: '0.01%' },
              { value: 0.0005, label: '0.05%' },
              { value: 0.001, label: '0.10%' },
              { value: 0.002, label: '0.20%' },
              { value: 0.005, label: '0.50%' },
            ]}
          />

          <ModernSelect
            label="Top Results"
            value={topN}
            onChange={(value) => setTopN(Number(value))}
            options={[
              { value: 10, label: '10' },
              { value: 20, label: '20' },
              { value: 50, label: '50' },
              { value: 100, label: '100' },
            ]}
          />

          <div className="flex items-center gap-2">
            <ModernToggle
              checked={autoRefresh}
              onChange={setAutoRefresh}
              label="Auto-refresh (30s)"
            />
          </div>

          <ModernButton
            variant="primary"
            onClick={fetchData}
            loading={loading}
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            }
          >
            Refresh
          </ModernButton>
        </div>
      </ModernCard>

      {/* Statistics */}
      {data?.statistics && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <ModernCard variant="flat" padding="md">
            <div className="text-xs text-text-secondary uppercase tracking-wider mb-1">
              Total Opportunities
            </div>
            <div className="text-2xl font-bold text-text-primary">
              {data.statistics.total_opportunities}
            </div>
          </ModernCard>

          <ModernCard variant="flat" padding="md">
            <div className="text-xs text-text-secondary uppercase tracking-wider mb-1">
              Max Spread
            </div>
            <div className="text-2xl font-bold text-success">
              {formatPercentageValue(data.statistics.max_spread)}
            </div>
          </ModernCard>

          <ModernCard variant="flat" padding="md">
            <div className="text-xs text-text-secondary uppercase tracking-wider mb-1">
              Max APR Spread
            </div>
            <div className="text-2xl font-bold text-warning">
              {formatAPR(data.statistics.max_apr_spread)}
            </div>
          </ModernCard>

          <ModernCard variant="flat" padding="md">
            <div className="text-xs text-text-secondary uppercase tracking-wider mb-1">
              Significant (|Z| &gt; 2)
            </div>
            <div className="text-2xl font-bold text-primary">
              {data.statistics.significant_count || 0}
            </div>
          </ModernCard>

          <ModernCard variant="flat" padding="md">
            <div className="text-xs text-text-secondary uppercase tracking-wider mb-1">
              Contracts Analyzed
            </div>
            <div className="text-2xl font-bold text-text-primary">
              {data.statistics.contracts_analyzed || 0}
            </div>
          </ModernCard>
        </div>
      )}

      {/* Data Table */}
      <ModernCard padding="none">
        <ModernTable
          columns={columns}
          data={data?.opportunities || []}
          striped
          hover
          stickyHeader
          emptyMessage="No arbitrage opportunities found with current filters"
        />
      </ModernCard>

      {/* Last Update */}
      {data && (
        <div className="text-center text-sm text-text-tertiary">
          Last updated: {new Date().toLocaleTimeString()}
          {autoRefresh && ' • Auto-refreshing every 30 seconds'}
        </div>
      )}
    </div>
  );
};

export default ArbitrageOpportunities;