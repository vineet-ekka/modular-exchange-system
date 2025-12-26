import React, { useState, useEffect, useMemo, useCallback, useDeferredValue, useRef } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getExpandedRowModel,
  SortingState,
  ExpandedState,
  Row,
} from '@tanstack/react-table';
import { useQueryClient } from '@tanstack/react-query';
import { cn } from '../../../lib/utils';
import { fetchContractsByAsset, ContractDetails } from '../../../services/api';
import { useGridData, queryKeys } from '../../../hooks/useDataQueries';
import { useContractPreload } from '../../../hooks/useContractPreload';
import { useExchangeFilter } from '../../../hooks/useExchangeFilter';
import { ExchangeFilterPanel } from '../ExchangeFilter';
import { DataTable } from './data-table';
import { ContractTable } from './ContractTable';
import { useColumns } from './useColumns';
import { AssetGridData, ViewMode, ViewModeOption } from './types';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';

const viewModeOptions: ViewModeOption[] = [
  { value: 'apr', label: 'APR', title: 'View Annualized Percentage Rate' },
  { value: '1h', label: '1H', title: 'View Cumulative Funding (1H)' },
  { value: '8h', label: '8H', title: 'View Cumulative Funding (8H)' },
  { value: '1d', label: '1D', title: 'View Cumulative Funding (1D)' },
  { value: '7d', label: '7D', title: 'View Cumulative Funding (7D)' },
];

const AssetFundingGridV2: React.FC = () => {
  const { data: gridResponse, isLoading: loading, error: queryError, refetch } = useGridData();
  const [searchTerm, setSearchTerm] = useState('');
  const deferredSearchTerm = useDeferredValue(searchTerm);
  const [contractsData, setContractsData] = useState<Record<string, ContractDetails[]>>({});
  const [loadingContracts, setLoadingContracts] = useState<Set<string>>(new Set());
  const [contractErrors, setContractErrors] = useState<Record<string, string>>({});
  const [autoExpandedAssets, setAutoExpandedAssets] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<ViewMode>('apr');
  const [sorting, setSorting] = useState<SortingState>([{ id: 'asset', desc: false }]);
  const [expanded, setExpanded] = useState<ExpandedState>({});
  const [userCollapsedAssets, setUserCollapsedAssets] = useState<Set<string>>(new Set());
  const fetchedAssetsRef = useRef<Set<string>>(new Set());

  const gridData = useMemo(() => {
    if (!gridResponse?.data) return [];
    return gridResponse.data.map((item: AssetGridData) => ({
      ...item,
      exchanges: Object.fromEntries(
        Object.entries(item.exchanges).map(([key, value]) => [key.toLowerCase(), value])
      ),
    }));
  }, [gridResponse]);

  const queryClient = useQueryClient();

  const topAssets = useMemo(() => {
    return gridData.slice(0, 100).map(item => item.asset);
  }, [gridData]);

  useContractPreload(topAssets, gridData.length > 0);

  const error = queryError ? queryError.message : null;

  const handleRefresh = () => {
    refetch();
  };

  const toggleAssetExpansion = useCallback(async (asset: string) => {
    const expandedObj = expanded === true ? {} : expanded;
    const isCurrentlyExpanded = expandedObj[asset] === true;

    if (isCurrentlyExpanded) {
      setUserCollapsedAssets(prev => new Set(prev).add(asset));
      setExpanded(prev => {
        const prevObj = prev === true ? {} : prev;
        const newState = { ...prevObj };
        delete newState[asset];
        return newState;
      });
    } else {
      const cachedContracts = queryClient.getQueryData<ContractDetails[]>(
        queryKeys.contractsByAsset(asset)
      );

      if (cachedContracts) {
        setContractsData(prev => ({ ...prev, [asset]: cachedContracts }));
      } else if (!contractsData[asset] && !loadingContracts.has(asset)) {
        setLoadingContracts(prev => new Set(prev).add(asset));
        try {
          const contracts = await queryClient.fetchQuery({
            queryKey: queryKeys.contractsByAsset(asset),
            queryFn: () => fetchContractsByAsset(asset),
            staleTime: 60000,
          });
          setContractsData(prev => ({
            ...prev,
            [asset]: contracts
          }));
          setContractErrors(prev => {
            const newErrors = { ...prev };
            delete newErrors[asset];
            return newErrors;
          });
        } catch (err) {
          const errorMessage = err instanceof Error ? err.message : 'Failed to fetch contracts';
          console.error(`Error fetching contracts for ${asset}:`, err);
          setContractErrors(prev => ({
            ...prev,
            [asset]: errorMessage
          }));
        } finally {
          setLoadingContracts(prev => {
            const newSet = new Set(prev);
            newSet.delete(asset);
            return newSet;
          });
        }
      }
      setExpanded(prev => {
        const prevObj = prev === true ? {} : prev;
        return { ...prevObj, [asset]: true };
      });
    }
  }, [expanded, contractsData, loadingContracts, queryClient]);

  const exchanges = useMemo(() => {
    if (gridData.length === 0) return [];
    const uniqueExchanges = new Set<string>();
    gridData.forEach((item: AssetGridData) => {
      Object.keys(item.exchanges).forEach(exchange => {
        uniqueExchanges.add(exchange);
      });
    });
    return Array.from(uniqueExchanges).sort();
  }, [gridData]);

  const {
    filterState,
    updateFilterState,
    filteredData: filterFilteredData,
    visibleExchanges,
  } = useExchangeFilter(gridData, exchanges, searchTerm, contractsData);

  useEffect(() => {
    setUserCollapsedAssets(new Set());
  }, [deferredSearchTerm]);

  useEffect(() => {
    if (!deferredSearchTerm || deferredSearchTerm.length < 2) {
      setAutoExpandedAssets(new Set());
      setExpanded({});
      return;
    }

    const controller = new AbortController();

    const fetchAndExpandContracts = async () => {
      const searchLower = deferredSearchTerm.toLowerCase();

      const assetsToFetch = gridData
        .filter(item => {
          const alreadyFetched = fetchedAssetsRef.current.has(item.asset);
          return !alreadyFetched && (
            item.asset.toLowerCase().includes(searchLower) ||
            searchLower.length > 3
          );
        })
        .slice(0, 10);

      if (assetsToFetch.length === 0) return;

      const fetchPromises = assetsToFetch.map(async (item) => {
        if (controller.signal.aborted) return null;

        try {
          const contracts = await queryClient.fetchQuery({
            queryKey: queryKeys.contractsByAsset(item.asset),
            queryFn: () => fetchContractsByAsset(item.asset),
            staleTime: 60000,
          });
          return { asset: item.asset, contracts, error: null };
        } catch (err) {
          if (err instanceof Error && err.name !== 'AbortError') {
            console.error(`Error fetching contracts for ${item.asset}:`, err);
          }
          return { asset: item.asset, contracts: null, error: err };
        }
      });

      const results = await Promise.allSettled(fetchPromises);

      const newContractsData: Record<string, ContractDetails[]> = {};
      const assetsToExpand = new Set<string>();

      results.forEach((result) => {
        if (result.status === 'fulfilled' && result.value && result.value.contracts) {
          const { asset, contracts } = result.value;
          newContractsData[asset] = contracts;

          const hasMatchingContract = contracts.some(contract =>
            contract.symbol.toLowerCase().includes(searchLower)
          );

          if (hasMatchingContract) {
            assetsToExpand.add(asset);
          }
        }
      });

      if (!controller.signal.aborted && Object.keys(newContractsData).length > 0) {
        fetchedAssetsRef.current = new Set([
          ...fetchedAssetsRef.current,
          ...Object.keys(newContractsData)
        ]);
        setContractsData(prev => ({ ...prev, ...newContractsData }));
        setAutoExpandedAssets(assetsToExpand);
        setExpanded(prev => {
          const prevObj = prev === true ? {} : prev;
          const newState = { ...prevObj };
          assetsToExpand.forEach(asset => {
            if (!userCollapsedAssets.has(asset)) {
              newState[asset] = true;
            }
          });
          return newState;
        });
      }
    };

    fetchAndExpandContracts();

    return () => {
      controller.abort();
    };
  }, [deferredSearchTerm, gridData, userCollapsedAssets, queryClient]);

  const filteredContractsMap = useMemo(() => {
    const result: Record<string, ContractDetails[]> = {};
    Object.keys(contractsData).forEach(asset => {
      result[asset] = contractsData[asset].filter(contract =>
        filterState.selectedExchanges.has(contract.exchange.toLowerCase())
      );
    });
    return result;
  }, [contractsData, filterState.selectedExchanges]);

  const contractCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    Object.entries(filteredContractsMap).forEach(([asset, contracts]) => {
      counts[asset] = contracts.length;
    });
    return counts;
  }, [filteredContractsMap]);

  const columns = useColumns(
    visibleExchanges,
    viewMode,
    filterState.highlightMissing
  );

  const table = useReactTable({
    data: filterFilteredData,
    columns,
    state: {
      sorting,
      expanded,
    },
    onSortingChange: setSorting,
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowId: (row) => row.asset,
    autoResetPageIndex: false,
    autoResetExpanded: false,
    enableRowSelection: false,
    enableMultiRowSelection: false,
  });

  const renderSubComponent = useCallback((row: Row<AssetGridData>) => {
    const asset = row.original.asset;
    const contracts = filteredContractsMap[asset];
    const isLoading = loadingContracts.has(asset);
    const assetError = contractErrors[asset];

    if (isLoading) {
      return <ContractTable contracts={[]} asset={asset} searchTerm={searchTerm} loading={true} />;
    }

    if (assetError) {
      return (
        <div className="p-4 text-center text-red-500">
          Error loading contracts for {asset}: {assetError}
        </div>
      );
    }

    if (!contracts || contracts.length === 0) {
      return (
        <div className="p-4 text-center text-gray-500">
          {contractsData[asset] && contractsData[asset].length > 0
            ? `No contracts match selected exchanges for ${asset}`
            : `No contracts found for ${asset}`}
        </div>
      );
    }

    return <ContractTable contracts={contracts} asset={asset} searchTerm={searchTerm} />;
  }, [filteredContractsMap, loadingContracts, contractErrors, searchTerm, contractsData]);

  if (error && gridData.length === 0) {
    return (
      <div className="p-6 text-center">
        <div className="text-red-500 mb-4">Error: {error}</div>
        <Button onClick={handleRefresh}>Retry</Button>
      </div>
    );
  }

  return (
    <div>
      <div className="bg-background shadow-sm border-y border-border overflow-hidden">
        <div className="px-6 py-4 border-b border-border bg-muted">
          <div className="flex justify-between items-center">
            <ExchangeFilterPanel
              exchanges={exchanges}
              selectedExchanges={filterState.selectedExchanges}
              onExchangesChange={(selected) => updateFilterState({ selectedExchanges: selected })}
              filterState={filterState}
              onFilterStateChange={updateFilterState}
              size="compact"
            />
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-1 bg-background border border-border rounded shadow-sm">
                {viewModeOptions.map((mode) => (
                  <Button
                    key={mode.value}
                    onClick={() => setViewMode(mode.value)}
                    variant={viewMode === mode.value ? "default" : "ghost"}
                    size="sm"
                    className={cn(
                      'px-3 py-1 text-xs font-medium transition-colors',
                      viewMode === mode.value
                        ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                    )}
                    title={mode.title}
                  >
                    {mode.label}
                  </Button>
                ))}
              </div>

              <Button
                onClick={handleRefresh}
                variant="default"
                size="sm"
              >
                Refresh
              </Button>

              <span className="text-sm text-muted-foreground">
                {filterFilteredData.length} assets
                {searchTerm && autoExpandedAssets.size > 0 && ` (${autoExpandedAssets.size} with matching contracts)`}
              </span>

              <Input
                type="text"
                placeholder="Search assets or contract names..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-64 text-sm"
              />
            </div>
          </div>
        </div>

        <DataTable
          table={table}
          loading={loading}
          autoExpandedAssets={autoExpandedAssets}
          onToggleExpand={toggleAssetExpansion}
          renderSubComponent={renderSubComponent}
          viewMode={viewMode}
          contractCounts={contractCounts}
        />

        <div className="px-6 py-3 border-t border-border bg-muted flex items-center justify-between text-xs">
          <div className="flex items-center space-x-4">
            <span className="text-muted-foreground font-medium">
              {viewMode === 'apr'
                ? 'APR (Annualized):'
                : `Projected Funding (${viewMode.toUpperCase()}):`}
            </span>
            <span className="text-green-600">Positive (Long pays Short)</span>
            <span className="text-red-600">Negative (Short pays Long)</span>
            <span className="text-muted-foreground">No Data</span>
          </div>
          <div className="text-muted-foreground">
            {viewMode === 'apr'
              ? 'Click arrow to expand contracts'
              : `Projected funding over ${viewMode === '1h' ? '1 hour' : viewMode === '8h' ? '8 hours' : viewMode === '1d' ? '1 day' : '1 week'} at current rate - Click arrow to expand contracts`}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AssetFundingGridV2;
