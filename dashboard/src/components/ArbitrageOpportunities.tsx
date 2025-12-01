import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useArbitrageOpportunities } from '../hooks/useDataQueries';
import { ContractArbitrageOpportunity } from '../services/arbitrage';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { SimpleSelect } from './ui/simple-select';
import { DataTable } from './ui/data-table';
import { Badge } from './ui/badge';
import { Tooltip } from './ui/tooltip';
import { Pagination } from './ui/pagination';
import clsx from 'clsx';
import { useArbitrageFilter } from '../hooks/useArbitrageFilter';
import ArbitrageFilterPanel from './Arbitrage/ArbitrageFilterPanel';

const ArbitrageOpportunities: React.FC = () => {
  const navigate = useNavigate();
  const [minSpread, setMinSpread] = useState(0.0005);
  const [pageSize, setPageSize] = useState(20);
  const [currentPage, setCurrentPage] = useState(1);
  const [sortKey, setSortKey] = useState<string | undefined>(undefined);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const {
    filterState,
    updateFilter,
    resetFilter,
    filterCount,
    buildQueryParams
  } = useArbitrageFilter();

  const filterParams = useMemo(() => buildQueryParams(), [buildQueryParams]);

  const {
    data,
    isLoading: loading,
    isFetching,
    error: queryError,
    refetch
  } = useArbitrageOpportunities(minSpread, currentPage, pageSize, filterParams);

  const error = queryError ? 'Failed to fetch arbitrage opportunities' : null;

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
      <Badge variant={variant}>
        Z: {zScore.toFixed(2)}
      </Badge>
    );
  };


  const handleSort = (key: string, direction: 'asc' | 'desc') => {
    setSortKey(key);
    setSortDirection(direction);
  };

  const handleRowClick = (opportunity: ContractArbitrageOpportunity) => {
    navigate(
      `/arbitrage/${opportunity.asset}/${opportunity.long_exchange}/${opportunity.short_exchange}`,
      { state: { opportunity } }
    );
  };

  const sortData = (dataToSort: ContractArbitrageOpportunity[]) => {
    if (!sortKey) return dataToSort;

    const sorted = [...dataToSort].sort((a, b) => {
      let aValue: number | null = null;
      let bValue: number | null = null;

      switch (sortKey) {
        case 'rateSpread':
          aValue = a.rate_spread_pct;
          bValue = b.rate_spread_pct;
          break;
        default:
          return 0;
      }

      // Handle null values
      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;

      // Sort based on direction
      if (sortDirection === 'asc') {
        return aValue - bValue;
      } else {
        return bValue - aValue;
      }
    });

    return sorted;
  };


  if (loading && !data) {
    return (
      <Card className="bg-white border border-border shadow-sm p-8">
        <div className="flex flex-col items-center justify-center py-8">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-text-secondary">Loading arbitrage opportunities...</p>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-white border border-border shadow-sm p-8">
        <div className="text-center py-8">
          <p className="text-danger text-lg font-medium">{error}</p>
          <Button
            variant="default"
            onClick={() => refetch()}
            className="mt-4"
          >
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  const columns = [
    {
      key: 'asset',
      header: 'Asset',
      accessor: (row: ContractArbitrageOpportunity) => (
        <span className="text-sm font-bold text-text-primary">{row.asset}</span>
      ),
      align: 'left' as const,
      width: '10%',
    },
    {
      key: 'long',
      header: 'Long Position',
      accessor: (row: ContractArbitrageOpportunity) => (
        <div>
          <div className="font-medium">{row.long_contract}</div>
          <div className="text-sm text-text-tertiary">{row.long_exchange}</div>
          <div className={clsx('text-sm font-mono', row.long_rate < 0 ? 'text-success' : 'text-danger')}>
            {formatPercentage(row.long_rate)}
          </div>
        </div>
      ),
      align: 'left' as const,
      width: '15%',
    },
    {
      key: 'short',
      header: 'Short Position',
      accessor: (row: ContractArbitrageOpportunity) => (
        <div>
          <div className="font-medium">{row.short_contract}</div>
          <div className="text-sm text-text-tertiary">{row.short_exchange}</div>
          <div className={clsx('text-sm font-mono', row.short_rate > 0 ? 'text-success' : 'text-danger')}>
            {formatPercentage(row.short_rate)}
          </div>
        </div>
      ),
      align: 'left' as const,
      width: '15%',
    },
    {
      key: 'rateSpread',
      header: (
        <Tooltip
          content="The funding rate difference between long and short positions. APR Spread shows the annualized percentage return from this arbitrage opportunity."
          position="bottom"
        >
          <span>Funding Rate Spread</span>
        </Tooltip>
      ),
      accessor: (row: ContractArbitrageOpportunity) => (
        <div className="text-center">
          <div className="text-sm font-bold text-success">
            {formatPercentageValue(row.rate_spread_pct)}
          </div>
          <div className="text-sm text-text-secondary">
            APR: {formatAPR(row.apr_spread)}
          </div>
        </div>
      ),
      align: 'center' as const,
      width: '10%',
      sortable: true,
    },
    {
      key: 'intervals',
      header: 'Intervals',
      accessor: (row: ContractArbitrageOpportunity) => (
        <div className="text-sm">
          {row.long_interval_hours}h / {row.short_interval_hours}h
        </div>
      ),
      align: 'center' as const,
      width: '8%',
    },
    {
      key: 'zscores',
      header: (
        <Tooltip
          content="Z-score of the APR spread combination. Calculated as (Current APR Spread - Mean Historical APR Spread) / Standard Deviation. Values >2 or <-2 indicate statistically significant opportunities."
          position="bottom"
        >
          <span>Spread Z-Score</span>
        </Tooltip>
      ),
      accessor: (row: ContractArbitrageOpportunity) => (
        <div className="flex flex-col items-center gap-1">
          {row.spread_zscore !== null && row.spread_zscore !== undefined ? (
            <>
              {getZScoreBadge(row.spread_zscore)}
              {row.spread_mean !== null && row.spread_std_dev !== null && (
                <div className="text-xs text-text-tertiary">
                  μ={row.spread_mean.toFixed(1)}% σ={row.spread_std_dev.toFixed(1)}%
                </div>
              )}
            </>
          ) : (
            <span className="text-text-tertiary text-xs">No data</span>
          )}
        </div>
      ),
      align: 'center' as const,
      width: '12%',
    },
    {
      key: 'openInterest',
      header: 'Open Interest',
      accessor: (row: ContractArbitrageOpportunity) => (
        <div>
          <div className="text-sm">
            <span className="text-text-tertiary">L:</span>
            <span className="ml-1">{formatOpenInterest(row.long_open_interest)}</span>
          </div>
          <div className="text-sm">
            <span className="text-text-tertiary">S:</span>
            <span className="ml-1">{formatOpenInterest(row.short_open_interest)}</span>
          </div>
        </div>
      ),
      align: 'right' as const,
      width: '11%',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Filter Panel */}
      <ArbitrageFilterPanel
        filterState={filterState}
        onFilterChange={updateFilter}
        onApply={() => {
          setCurrentPage(1); // Reset to first page on filter apply
          refetch();
        }}
        onReset={() => {
          resetFilter();
          setCurrentPage(1);
          refetch();
        }}
      />

      {/* Controls */}
      <Card className="p-6">
        <div className="flex flex-wrap gap-4 items-end">
          <SimpleSelect
            label="Minimum Spread"
            value={minSpread}
            onChange={(value) => {
              setMinSpread(Number(value));
              setCurrentPage(1);
            }}
            options={[
              { value: 0.0001, label: '0.01%' },
              { value: 0.0005, label: '0.05%' },
              { value: 0.001, label: '0.10%' },
              { value: 0.002, label: '0.20%' },
              { value: 0.005, label: '0.50%' },
            ]}
          />

          <SimpleSelect
            label="Page Size"
            value={pageSize}
            onChange={(value) => {
              setPageSize(Number(value));
              setCurrentPage(1);
            }}
            options={[
              { value: 10, label: '10' },
              { value: 20, label: '20' },
              { value: 50, label: '50' },
            ]}
          />

          <Button
            variant="default"
            onClick={() => refetch()}
            loading={loading}
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            }
          >
            Refresh
          </Button>
        </div>
      </Card>

      {/* Statistics */}
      {data?.statistics && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <Card className="shadow-none border border-border bg-white p-4">
            <div className="text-xs text-text-secondary uppercase tracking-wider mb-1">
              Total Opportunities
            </div>
            <div className="text-2xl font-bold text-text-primary">
              {data?.statistics?.total_opportunities || 0}
            </div>
          </Card>

          <Card className="shadow-none border border-border bg-white p-4">
            <div className="text-xs text-text-secondary uppercase tracking-wider mb-1">
              Max Spread
            </div>
            <div className="text-2xl font-bold text-success">
              {formatPercentageValue(data?.statistics?.max_spread || 0)}
            </div>
          </Card>

          <Card className="shadow-none border border-border bg-white p-4">
            <div className="text-xs text-text-secondary uppercase tracking-wider mb-1">
              Max Daily Spread
            </div>
            <div className="text-2xl font-bold text-warning">
              {formatPercentageValue(data?.statistics?.max_daily_spread || 0)}
            </div>
          </Card>

          <Card className="shadow-none border border-border bg-white p-4">
            <div className="text-xs text-text-secondary uppercase tracking-wider mb-1">
              Max APR Spread
            </div>
            <div className="text-2xl font-bold text-warning">
              {formatAPR(data?.statistics?.max_apr_spread || 0)}
            </div>
          </Card>

          <Card className="shadow-none border border-border bg-white p-4">
            <div className="text-xs text-text-secondary uppercase tracking-wider mb-1">
              Contracts Analyzed
            </div>
            <div className="text-2xl font-bold text-text-primary">
              {data?.statistics?.contracts_analyzed || 0}
            </div>
          </Card>
        </div>
      )}

      {/* Data Table */}
      <Card className="p-0 relative">
        {/* Loading overlay for page transitions */}
        {isFetching && (
          <div className="absolute inset-0 bg-white/70 backdrop-blur-sm flex items-center justify-center z-20 rounded-lg">
            <div className="flex items-center gap-3 bg-white px-6 py-3 rounded-lg shadow-lg">
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-text-secondary font-medium">
                Loading page {currentPage}...
              </span>
            </div>
          </div>
        )}
        <DataTable
          columns={columns}
          data={sortData(data?.opportunities || [])}
          striped
          hover
          stickyHeader
          emptyMessage="No arbitrage opportunities found with current filters"
          onSort={handleSort}
          sortKey={sortKey}
          sortDirection={sortDirection}
          onRowClick={handleRowClick}
        />
      </Card>

      {/* Pagination */}
      {data?.pagination && data.pagination.total_pages > 1 && (
        <Card className="p-6">
          <Pagination
            currentPage={currentPage}
            totalPages={data.pagination.total_pages}
            pageSize={pageSize}
            totalItems={data.pagination.total}
            onPageChange={setCurrentPage}
          />
        </Card>
      )}

      {/* Last Update */}
      {data && (
        <div className="text-center text-sm text-text-tertiary">
          Last updated: {new Date().toLocaleTimeString()} • Auto-refreshing every 30 seconds
        </div>
      )}
    </div>
  );
};

export default React.memo(ArbitrageOpportunities);