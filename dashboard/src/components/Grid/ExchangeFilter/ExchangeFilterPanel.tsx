import React from 'react';
import { ExchangeFilterState } from '../../../types/exchangeFilter';
import { EXCHANGE_METADATA, ALL_EXCHANGES } from '../../../constants/exchangeMetadata';
import { DEFAULT_FILTER_STATE } from '../../../hooks/useFilterPersistence';
import ModernCard from '../../Modern/ModernCard';
import ModernMultiSelect from '../../Modern/ModernMultiSelect';

interface ExchangeFilterPanelProps {
  exchanges: string[];
  selectedExchanges: Set<string>;
  onExchangesChange: (selected: Set<string>) => void;
  filterState: ExchangeFilterState;
  onFilterStateChange: (state: Partial<ExchangeFilterState>) => void;
}

const ExchangeFilterPanel: React.FC<ExchangeFilterPanelProps> = ({
  exchanges,
  selectedExchanges,
  onExchangesChange,
  filterState,
  onFilterStateChange,
}) => {
  const toggleExpanded = () => {
    onFilterStateChange({ filterExpanded: !filterState.filterExpanded });
  };

  const exchangeOptions = exchanges.map(exchange => ({
    value: exchange,
    label: exchange.charAt(0).toUpperCase() + exchange.slice(1),
    count: EXCHANGE_METADATA[exchange]?.contracts || 0,
    color: EXCHANGE_METADATA[exchange]?.color,
  }));

  const handleSelectAll = () => {
    onExchangesChange(new Set(ALL_EXCHANGES));
  };

  const handleClearAll = () => {
    if (selectedExchanges.size > 1) {
      onExchangesChange(new Set([ALL_EXCHANGES[0]]));
    }
  };

  const handleInvert = () => {
    const inverted = new Set(
      ALL_EXCHANGES.filter(ex => !selectedExchanges.has(ex))
    );
    if (inverted.size > 0) {
      onExchangesChange(inverted);
    }
  };

  const handleReset = () => {
    onFilterStateChange(DEFAULT_FILTER_STATE);
    onExchangesChange(DEFAULT_FILTER_STATE.selectedExchanges);
  };

  const isFiltered = selectedExchanges.size < ALL_EXCHANGES.length ||
    filterState.hideEmptyAssets ||
    filterState.showOnlyCrossListed ||
    filterState.highlightMissing;

  return (
    <div className="mb-3">
      <ModernCard variant="flat" padding="none">
        <div className="px-3 py-2">
          <button
            onClick={toggleExpanded}
            className="flex items-center space-x-2 text-xs font-semibold text-text-primary hover:text-primary transition-colors"
          >
            <span className="text-gray-400 text-xs">
              {filterState.filterExpanded ? '▼' : '▶'}
            </span>
            <span>EXCHANGE FILTER</span>
            {isFiltered && (
              <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-blue-500 text-white rounded-full">
                Active
              </span>
            )}
          </button>
          {filterState.filterExpanded && (
            <div className="flex items-center space-x-2 mt-1.5">
              <span className="text-xs text-text-muted">
                {selectedExchanges.size} of {exchanges.length} selected
              </span>
              {isFiltered && (
                <button
                  onClick={handleReset}
                  className="text-xs text-blue-500 hover:text-blue-700 underline"
                >
                  Reset All
                </button>
              )}
            </div>
          )}
        </div>

        {filterState.filterExpanded && (
          <div className="px-3 pb-2 mt-2 pt-2 border-t border-border space-y-2.5">
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={handleSelectAll}
                className="px-2.5 py-1 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
              >
                Select All
              </button>
              <button
                onClick={handleClearAll}
                className="px-2.5 py-1 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
              >
                Clear
              </button>
              <button
                onClick={handleInvert}
                className="px-2.5 py-1 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
              >
                Invert
              </button>
            </div>

            <ModernMultiSelect
              options={exchangeOptions}
              value={selectedExchanges}
              onChange={onExchangesChange}
              placeholder="Select exchanges to display"
              size="compact"
            />

            <div className="flex flex-col gap-2">
              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filterState.hideEmptyAssets}
                  onChange={(e) => onFilterStateChange({ hideEmptyAssets: e.target.checked })}
                  className="w-3.5 h-3.5 text-blue-500 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-xs text-gray-700">Hide empty assets</span>
              </label>

              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filterState.showOnlyCrossListed}
                  onChange={(e) => onFilterStateChange({ showOnlyCrossListed: e.target.checked })}
                  className="w-3.5 h-3.5 text-blue-500 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-xs text-gray-700">Cross-listed only</span>
              </label>

              <label className="flex items-center space-x-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filterState.highlightMissing}
                  onChange={(e) => onFilterStateChange({ highlightMissing: e.target.checked })}
                  className="w-3.5 h-3.5 text-blue-500 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-xs text-gray-700">Highlight missing</span>
              </label>
            </div>
          </div>
        )}
      </ModernCard>
    </div>
  );
};

export default ExchangeFilterPanel;
