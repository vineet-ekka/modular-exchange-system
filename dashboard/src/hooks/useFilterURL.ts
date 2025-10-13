import { useEffect } from 'react';
import { ExchangeFilterState } from '../types/exchangeFilter';
import { ALL_EXCHANGES } from '../constants/exchangeMetadata';

export const syncStateToURL = (state: ExchangeFilterState): void => {
  const params = new URLSearchParams();

  if (state.selectedExchanges.size < ALL_EXCHANGES.length) {
    params.set('exchanges', [...state.selectedExchanges].sort().join(','));
  }

  if (state.hideEmptyAssets) {
    params.set('hideEmpty', 'true');
  }

  if (state.showOnlyCrossListed) {
    params.set('crosslisted', 'true');
  }

  if (state.highlightMissing) {
    params.set('highlight', 'true');
  }

  const url = params.toString() ? `?${params.toString()}` : window.location.pathname;
  window.history.replaceState(null, '', url);
};

export const loadStateFromURL = (): Partial<ExchangeFilterState> | null => {
  const params = new URLSearchParams(window.location.search);

  if (!params.has('exchanges') && !params.has('hideEmpty') && !params.has('crosslisted') && !params.has('highlight')) {
    return null;
  }

  const state: Partial<ExchangeFilterState> = {};

  if (params.has('exchanges')) {
    state.selectedExchanges = new Set(params.get('exchanges')?.split(',') || []);
  }

  if (params.has('hideEmpty')) {
    state.hideEmptyAssets = params.get('hideEmpty') === 'true';
  }

  if (params.has('crosslisted')) {
    state.showOnlyCrossListed = params.get('crosslisted') === 'true';
  }

  if (params.has('highlight')) {
    state.highlightMissing = params.get('highlight') === 'true';
  }

  return state;
};

export const useFilterURL = (
  filterState: ExchangeFilterState
): void => {
  useEffect(() => {
    syncStateToURL(filterState);
  }, [
    filterState.selectedExchanges,
    filterState.hideEmptyAssets,
    filterState.showOnlyCrossListed,
    filterState.highlightMissing
  ]);
};
