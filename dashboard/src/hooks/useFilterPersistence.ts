import { useEffect } from 'react';
import { ExchangeFilterState } from '../types/exchangeFilter';
import { ALL_EXCHANGES } from '../constants/exchangeMetadata';

const STORAGE_KEYS = {
  SELECTED_EXCHANGES: 'assetGrid.selectedExchanges',
  FILTER_COLLAPSED: 'assetGrid.filterCollapsed',
  HIDE_EMPTY_ASSETS: 'assetGrid.hideEmptyAssets',
  SHOW_ONLY_CROSSLISTED: 'assetGrid.showOnlyCrossListed',
  HIGHLIGHT_MISSING: 'assetGrid.highlightMissing'
};

export const DEFAULT_FILTER_STATE: ExchangeFilterState = {
  selectedExchanges: new Set(ALL_EXCHANGES),
  filterExpanded: false,
  hideEmptyAssets: false,
  showOnlyCrossListed: false,
  highlightMissing: false
};

export const saveFilterState = (state: ExchangeFilterState): void => {
  try {
    localStorage.setItem(
      STORAGE_KEYS.SELECTED_EXCHANGES,
      JSON.stringify([...state.selectedExchanges])
    );
    localStorage.setItem(
      STORAGE_KEYS.FILTER_COLLAPSED,
      String(state.filterExpanded)
    );
    localStorage.setItem(
      STORAGE_KEYS.HIDE_EMPTY_ASSETS,
      String(state.hideEmptyAssets)
    );
    localStorage.setItem(
      STORAGE_KEYS.SHOW_ONLY_CROSSLISTED,
      String(state.showOnlyCrossListed)
    );
    localStorage.setItem(
      STORAGE_KEYS.HIGHLIGHT_MISSING,
      String(state.highlightMissing)
    );
  } catch (error) {
    console.error('Failed to save filter state:', error);
  }
};

export const loadFilterState = (): ExchangeFilterState => {
  try {
    const savedExchanges = localStorage.getItem(STORAGE_KEYS.SELECTED_EXCHANGES);
    const savedCollapsed = localStorage.getItem(STORAGE_KEYS.FILTER_COLLAPSED);
    const savedHideEmpty = localStorage.getItem(STORAGE_KEYS.HIDE_EMPTY_ASSETS);
    const savedCrossListed = localStorage.getItem(STORAGE_KEYS.SHOW_ONLY_CROSSLISTED);
    const savedHighlightMissing = localStorage.getItem(STORAGE_KEYS.HIGHLIGHT_MISSING);

    return {
      ...DEFAULT_FILTER_STATE,
      selectedExchanges: savedExchanges
        ? new Set(JSON.parse(savedExchanges))
        : DEFAULT_FILTER_STATE.selectedExchanges,
      filterExpanded: savedCollapsed === 'true',
      hideEmptyAssets: savedHideEmpty === 'true',
      showOnlyCrossListed: savedCrossListed === 'true',
      highlightMissing: savedHighlightMissing === 'true'
    };
  } catch (error) {
    console.error('Failed to load filter state:', error);
    return DEFAULT_FILTER_STATE;
  }
};

export const useFilterPersistence = (
  filterState: ExchangeFilterState
): void => {
  useEffect(() => {
    saveFilterState(filterState);
  }, [filterState]);
};
