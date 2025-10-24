import React, { useState } from 'react';
import { ArbitrageFilterState } from '../../types/arbitrageFilter';
import { useFilterCount } from '../../hooks/useArbitrageFilter';
import { ALL_EXCHANGES } from '../../constants/exchangeMetadata';
import AssetAutocomplete from './AssetAutocomplete';
import IntervalSelector from './IntervalSelector';
import APRRangeFilter from './APRRangeFilter';
import LiquidityFilter from './LiquidityFilter';
import styles from './ArbitrageFilter.module.css';

interface ArbitrageFilterPanelProps {
  filterState: ArbitrageFilterState;
  onFilterChange: (state: Partial<ArbitrageFilterState>) => void;
  onApply: () => void;
  onReset: () => void;
}

export const ArbitrageFilterPanel: React.FC<ArbitrageFilterPanelProps> = ({
  filterState,
  onFilterChange,
  onApply,
  onReset
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const filterCount = useFilterCount(filterState);

  const handleClear = () => {
    onReset();
  };

  const handleApply = () => {
    onApply();
    setIsOpen(false);
  };

  const toggleExchange = (exchange: string) => {
    const newExchanges = new Set(filterState.selectedExchanges);
    if (newExchanges.has(exchange)) {
      newExchanges.delete(exchange);
    } else {
      newExchanges.add(exchange);
    }
    onFilterChange({ selectedExchanges: newExchanges });
  };

  const removeFilter = (key: string, value?: string) => {
    switch (key) {
      case 'assets':
        if (value) {
          onFilterChange({
            selectedAssets: filterState.selectedAssets.filter(a => a.symbol !== value)
          });
        }
        break;
      case 'exchanges':
        onFilterChange({ selectedExchanges: new Set() });
        break;
      case 'intervals':
        onFilterChange({ selectedIntervals: new Set() });
        break;
      case 'apr':
        onFilterChange({ minApr: null, maxApr: null });
        break;
      case 'liquidity':
        onFilterChange({ minOIEither: null, minOICombined: null });
        break;
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.filterTrigger}>
        {/* Filter Button */}
        <button
          className={`${styles.filterBtn} ${filterCount > 0 ? styles.active : ''}`}
          onClick={() => setIsOpen(!isOpen)}
        >
          <svg className={styles.filterIcon} viewBox="0 0 16 16" fill="currentColor">
            <path d="M1 3.5A.5.5 0 0 1 1.5 3h13a.5.5 0 0 1 0 1h-13A.5.5 0 0 1 1 3.5zM4 7.5A.5.5 0 0 1 4.5 7h7a.5.5 0 0 1 0 1h-7A.5.5 0 0 1 4 7.5zM6.5 11a.5.5 0 0 0 0 1h3a.5.5 0 0 0 0-1h-3z"/>
          </svg>
          Filters
          {filterCount > 0 && (
            <span className={styles.filterCount}>{filterCount}</span>
          )}
        </button>

        {/* Filter Dropdown */}
        <div className={`${styles.filterDropdown} ${!isOpen ? styles.hidden : ''}`}>
          <div className={styles.filterHeader}>
            <span className={styles.filterTitle}>Filter Options</span>
            <div className={styles.filterActions}>
              <button className={styles.filterActionBtn} onClick={handleClear}>
                Clear
              </button>
              <button className={`${styles.filterActionBtn} ${styles.apply}`} onClick={handleApply}>
                Apply
              </button>
            </div>
          </div>

          <div className={styles.filterContent}>
            {/* Asset Search */}
            <AssetAutocomplete
              selectedAssets={filterState.selectedAssets}
              onChange={(assets) => onFilterChange({ selectedAssets: assets })}
            />

            {/* Exchange Grid */}
            <div className={styles.filterSection}>
              <div className={styles.sectionLabel}>Exchanges</div>
              <div className={styles.exchangeGrid}>
                {ALL_EXCHANGES.map(exchange => (
                  <div
                    key={exchange}
                    className={`${styles.exchangeItem} ${
                      filterState.selectedExchanges.has(exchange) ? styles.selected : ''
                    }`}
                    onClick={() => toggleExchange(exchange)}
                  >
                    <input
                      type="checkbox"
                      className={styles.exchangeCheckbox}
                      checked={filterState.selectedExchanges.has(exchange)}
                      onChange={() => toggleExchange(exchange)}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <label className={styles.exchangeLabel}>
                      {exchange.charAt(0).toUpperCase() + exchange.slice(1)}
                    </label>
                  </div>
                ))}
              </div>
            </div>

            {/* Funding Intervals */}
            <IntervalSelector
              selectedIntervals={filterState.selectedIntervals}
              onChange={(intervals) => onFilterChange({ selectedIntervals: intervals })}
            />

            {/* APR Range */}
            <APRRangeFilter
              minApr={filterState.minApr}
              maxApr={filterState.maxApr}
              onChange={(range) => onFilterChange(range)}
            />

            {/* Liquidity Filter */}
            <LiquidityFilter
              minOIEither={filterState.minOIEither}
              minOICombined={filterState.minOICombined}
              onChange={(liquidity) => onFilterChange(liquidity)}
            />
          </div>

          {/* Active Filters Footer */}
          <div className={styles.activeFilters}>
            {filterCount === 0 ? (
              <span className={styles.noFilters}>No filters applied</span>
            ) : (
              <>
                {filterState.selectedAssets.map(asset => (
                  <div key={asset.symbol} className={styles.filterTag}>
                    <span>Asset: {asset.symbol}</span>
                    <span
                      className={styles.remove}
                      onClick={() => removeFilter('assets', asset.symbol)}
                    >
                      ×
                    </span>
                  </div>
                ))}

                {filterState.selectedExchanges.size > 0 &&
                 filterState.selectedExchanges.size < ALL_EXCHANGES.length && (
                  <div className={styles.filterTag}>
                    <span>{filterState.selectedExchanges.size} Exchanges</span>
                    <span
                      className={styles.remove}
                      onClick={() => removeFilter('exchanges')}
                    >
                      ×
                    </span>
                  </div>
                )}

                {filterState.selectedIntervals.size > 0 &&
                 filterState.selectedIntervals.size < 4 && (
                  <div className={styles.filterTag}>
                    <span>{filterState.selectedIntervals.size} Intervals</span>
                    <span
                      className={styles.remove}
                      onClick={() => removeFilter('intervals')}
                    >
                      ×
                    </span>
                  </div>
                )}

                {(filterState.minApr !== null || filterState.maxApr !== null) && (
                  <div className={styles.filterTag}>
                    <span>
                      APR: {filterState.minApr !== null ? `>${filterState.minApr}%` : ''}
                      {filterState.minApr !== null && filterState.maxApr !== null ? ' - ' : ''}
                      {filterState.maxApr !== null ? `<${filterState.maxApr}%` : ''}
                    </span>
                    <span
                      className={styles.remove}
                      onClick={() => removeFilter('apr')}
                    >
                      ×
                    </span>
                  </div>
                )}

                {(filterState.minOIEither !== null || filterState.minOICombined !== null) && (
                  <div className={styles.filterTag}>
                    <span>Liquidity filters</span>
                    <span
                      className={styles.remove}
                      onClick={() => removeFilter('liquidity')}
                    >
                      ×
                    </span>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ArbitrageFilterPanel;