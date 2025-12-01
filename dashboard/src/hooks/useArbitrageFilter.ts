import { useState, useEffect, useCallback, useRef } from 'react';
import debounce from 'lodash/debounce';
import { ArbitrageFilterState, DEFAULT_ARBITRAGE_FILTER_STATE, Asset } from '../types/arbitrageFilter';
import { ALL_EXCHANGES } from '../constants/exchangeMetadata';

const STORAGE_KEY = 'arbitrage_filter_state';
const DEBOUNCE_MS = 500;

export const useArbitrageFilter = () => {
  const [filterState, setFilterState] = useState<ArbitrageFilterState>(() => {
    // Load from localStorage on initialization
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return {
          ...parsed,
          selectedExchanges: new Set(parsed.selectedExchanges),
          selectedIntervals: new Set(parsed.selectedIntervals),
        };
      }
    } catch (error) {
      console.error('Failed to load filter state from localStorage:', error);
    }
    return DEFAULT_ARBITRAGE_FILTER_STATE;
  });

  const debouncedSaveRef = useRef(
    debounce((state: ArbitrageFilterState) => {
      try {
        const toSave = {
          ...state,
          selectedExchanges: Array.from(state.selectedExchanges),
          selectedIntervals: Array.from(state.selectedIntervals),
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
      } catch (error) {
        console.error('Failed to save filter state to localStorage:', error);
      }
    }, DEBOUNCE_MS)
  );

  useEffect(() => {
    debouncedSaveRef.current(filterState);
  }, [filterState]);

  useEffect(() => {
    const debouncedFn = debouncedSaveRef.current;
    return () => {
      debouncedFn.cancel();
    };
  }, []);

  // Update partial filter state
  const updateFilter = useCallback((partial: Partial<ArbitrageFilterState>) => {
    setFilterState(prev => ({ ...prev, ...partial }));
  }, []);

  // Reset to defaults
  const resetFilter = useCallback(() => {
    setFilterState(DEFAULT_ARBITRAGE_FILTER_STATE);
  }, []);

  // Calculate filter count
  const filterCount = useCallback(() => {
    let count = 0;

    // Assets
    count += filterState.selectedAssets.length;

    // Exchanges (only count if not all selected)
    if (filterState.selectedExchanges.size > 0 && filterState.selectedExchanges.size < ALL_EXCHANGES.length) {
      count += 1;
    }

    // Intervals (only count if not all selected)
    if (filterState.selectedIntervals.size > 0 && filterState.selectedIntervals.size < 4) {
      count += 1;
    }

    // APR range
    if (filterState.minApr !== null) count += 1;
    if (filterState.maxApr !== null) count += 1;

    // Liquidity
    if (filterState.minOIEither !== null) count += 1;
    if (filterState.minOICombined !== null) count += 1;

    return count;
  }, [filterState]);

  // Remove individual filter
  const removeFilter = useCallback((key: keyof ArbitrageFilterState, value?: any) => {
    switch (key) {
      case 'selectedAssets':
        if (value) {
          setFilterState(prev => ({
            ...prev,
            selectedAssets: prev.selectedAssets.filter(a => a.symbol !== value)
          }));
        } else {
          setFilterState(prev => ({ ...prev, selectedAssets: [] }));
        }
        break;

      case 'selectedExchanges':
        setFilterState(prev => ({
          ...prev,
          selectedExchanges: new Set()
        }));
        break;

      case 'selectedIntervals':
        setFilterState(prev => ({
          ...prev,
          selectedIntervals: new Set()
        }));
        break;

      case 'minApr':
      case 'maxApr':
      case 'minOIEither':
      case 'minOICombined':
        setFilterState(prev => ({ ...prev, [key]: null }));
        break;
    }
  }, []);

  // Build API query parameters
  const buildQueryParams = useCallback(() => {
    const params: Record<string, any> = {};

    if (filterState.selectedAssets.length > 0) {
      params.assets = filterState.selectedAssets.map(a => a.symbol);
    }

    if (filterState.selectedExchanges.size > 0) {
      params.exchanges = Array.from(filterState.selectedExchanges);
    }

    if (filterState.selectedIntervals.size > 0) {
      params.intervals = Array.from(filterState.selectedIntervals);
    }

    if (filterState.minApr !== null) params.min_apr = filterState.minApr;
    if (filterState.maxApr !== null) params.max_apr = filterState.maxApr;
    if (filterState.minOIEither !== null) params.min_oi_either = filterState.minOIEither;
    if (filterState.minOICombined !== null) params.min_oi_combined = filterState.minOICombined;

    return params;
  }, [filterState]);

  return {
    filterState,
    updateFilter,
    resetFilter,
    filterCount: filterCount(),
    removeFilter,
    buildQueryParams,
  };
};

export const useFilterCount = (filterState: ArbitrageFilterState): number => {
  let count = 0;

  count += filterState.selectedAssets.length;

  if (filterState.selectedExchanges.size > 0 && filterState.selectedExchanges.size < ALL_EXCHANGES.length) {
    count += 1;
  }

  if (filterState.selectedIntervals.size > 0 && filterState.selectedIntervals.size < 4) {
    count += 1;
  }

  if (filterState.minApr !== null) count += 1;
  if (filterState.maxApr !== null) count += 1;
  if (filterState.minOIEither !== null) count += 1;
  if (filterState.minOICombined !== null) count += 1;

  return count;
};