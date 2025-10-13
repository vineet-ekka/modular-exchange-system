import { useState, useMemo, useCallback } from 'react';
import { ExchangeFilterState, AssetGridData } from '../types/exchangeFilter';
import {
  DEFAULT_FILTER_STATE,
  loadFilterState,
  useFilterPersistence
} from './useFilterPersistence';
import { loadStateFromURL, useFilterURL } from './useFilterURL';
import { getVisibleExchanges, filterAssetsByEmptyData, filterAssetsByCrossListed } from '../utils/filterAlgorithms';
import { ALL_EXCHANGES } from '../constants/exchangeMetadata';

export const useExchangeFilter = (
  gridData: AssetGridData[],
  exchanges: string[],
  searchTerm: string,
  contractsData: Record<string, any[]>
) => {
  const [filterState, setFilterState] = useState<ExchangeFilterState>(() => {
    const urlState = loadStateFromURL();
    const savedState = loadFilterState();

    if (urlState && Object.keys(urlState).length > 0) {
      return { ...DEFAULT_FILTER_STATE, ...urlState };
    }

    return savedState;
  });

  useFilterPersistence(filterState);
  useFilterURL(filterState);

  const visibleExchanges = useMemo(
    () => getVisibleExchanges(exchanges, filterState.selectedExchanges),
    [exchanges, filterState.selectedExchanges]
  );

  const filteredData = useMemo(() => {
    let result = gridData;

    if (searchTerm && searchTerm.length >= 2) {
      const searchLower = searchTerm.toLowerCase();
      result = result.filter(asset =>
        asset.asset.toLowerCase().includes(searchLower) ||
        (contractsData[asset.asset] || []).some(contract =>
          contract.symbol.toLowerCase().includes(searchLower)
        )
      );
    }

    if (filterState.hideEmptyAssets) {
      result = filterAssetsByEmptyData(result, filterState.selectedExchanges);
    }

    if (filterState.showOnlyCrossListed) {
      result = filterAssetsByCrossListed(result, filterState.selectedExchanges);
    }

    return result;
  }, [gridData, searchTerm, contractsData, filterState.hideEmptyAssets, filterState.showOnlyCrossListed, filterState.selectedExchanges]);

  const updateFilterState = useCallback((updates: Partial<ExchangeFilterState>) => {
    setFilterState(prev => ({ ...prev, ...updates }));
  }, []);

  return {
    filterState,
    setFilterState,
    updateFilterState,
    filteredData,
    visibleExchanges,
  };
};
