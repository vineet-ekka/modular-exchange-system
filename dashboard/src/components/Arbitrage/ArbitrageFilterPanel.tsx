import React, { useState, useCallback, memo } from 'react';
import { ArbitrageFilterState } from '../../types/arbitrageFilter';
import { useFilterCount } from '../../hooks/useArbitrageFilter';
import { ALL_EXCHANGES } from '../../constants/exchangeMetadata';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import { cn } from '@/lib/utils';
import AssetAutocomplete from './AssetAutocomplete';
import IntervalSelector from './IntervalSelector';
import APRRangeFilter from './APRRangeFilter';
import LiquidityFilter from './LiquidityFilter';

interface ExchangeCheckboxProps {
  exchange: string;
  selected: boolean;
  onToggle: (exchange: string) => void;
}

const ExchangeCheckbox = memo<ExchangeCheckboxProps>(({ exchange, selected, onToggle }) => (
  <div
    className={cn(
      "flex items-center p-2.5 px-3 bg-background border rounded cursor-pointer transition-all text-sm",
      selected
        ? "bg-blue-50 border-blue-500"
        : "border-border hover:bg-muted hover:border-gray-300"
    )}
    onClick={() => onToggle(exchange)}
  >
    <Checkbox
      checked={selected}
      onCheckedChange={() => onToggle(exchange)}
      onClick={(e) => e.stopPropagation()}
      className="mr-2"
    />
    <Label className="text-foreground font-medium cursor-pointer flex-1">
      {exchange.charAt(0).toUpperCase() + exchange.slice(1)}
    </Label>
  </div>
));

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

  const toggleExchange = useCallback((exchange: string) => {
    const newExchanges = new Set(filterState.selectedExchanges);
    if (newExchanges.has(exchange)) {
      newExchanges.delete(exchange);
    } else {
      newExchanges.add(exchange);
    }
    onFilterChange({ selectedExchanges: newExchanges });
  }, [filterState.selectedExchanges, onFilterChange]);

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
    <div>
      <div className="relative inline-block">
        {/* Filter Button */}
        <Button
          variant={filterCount > 0 ? "default" : "outline"}
          onClick={() => setIsOpen(!isOpen)}
          className="gap-2"
        >
          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
            <path d="M1 3.5A.5.5 0 0 1 1.5 3h13a.5.5 0 0 1 0 1h-13A.5.5 0 0 1 1 3.5zM4 7.5A.5.5 0 0 1 4.5 7h7a.5.5 0 0 1 0 1h-7A.5.5 0 0 1 4 7.5zM6.5 11a.5.5 0 0 0 0 1h3a.5.5 0 0 0 0-1h-3z"/>
          </svg>
          Filters
          {filterCount > 0 && (
            <Badge
              variant={filterCount > 0 ? "secondary" : "default"}
              className={cn(
                "ml-1 min-w-5 h-4.5 px-1.5 text-xs font-semibold",
                filterCount > 0 && "bg-white/90 text-primary"
              )}
            >
              {filterCount}
            </Badge>
          )}
        </Button>

        {/* Filter Dropdown */}
        <div className={cn(
          "absolute top-full left-0 mt-2 w-[440px] bg-card border border-border rounded-lg shadow-lg z-50 overflow-hidden transition-all",
          !isOpen && "hidden"
        )}>
          {/* Header */}
          <div className="p-4 px-5 bg-muted border-b border-border flex justify-between items-center">
            <span className="text-foreground text-sm font-semibold uppercase tracking-wide">
              Filter Options
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleClear}>
                Clear
              </Button>
              <Button variant="default" size="sm" onClick={handleApply}>
                Apply
              </Button>
            </div>
          </div>

          {/* Content */}
          <div className="p-5 bg-card max-h-[460px] overflow-y-auto">
            {/* Asset Search */}
            <AssetAutocomplete
              selectedAssets={filterState.selectedAssets}
              onChange={(assets) => onFilterChange({ selectedAssets: assets })}
            />

            {/* Exchange Grid */}
            <div className="mb-6">
              <div className="text-muted-foreground text-xs font-semibold uppercase tracking-wider mb-3">
                Exchanges
              </div>
              <div className="grid grid-cols-2 gap-2">
                {ALL_EXCHANGES.map(exchange => (
                  <ExchangeCheckbox
                    key={exchange}
                    exchange={exchange}
                    selected={filterState.selectedExchanges.has(exchange)}
                    onToggle={toggleExchange}
                  />
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
          <div className="p-3 px-5 bg-muted border-t border-border flex flex-wrap gap-2 min-h-[44px] items-center">
            {filterCount === 0 ? (
              <span className="text-muted-foreground text-xs italic">No filters applied</span>
            ) : (
              <>
                {filterState.selectedAssets.map(asset => (
                  <Badge
                    key={asset.symbol}
                    variant="outline"
                    className="gap-1.5 py-1 px-2.5 bg-background hover:bg-muted cursor-default"
                  >
                    <span>Asset: {asset.symbol}</span>
                    <span
                      className="inline-flex items-center justify-center w-3.5 h-3.5 bg-gray-500 hover:bg-gray-600 rounded-full text-white text-xs leading-none cursor-pointer"
                      onClick={() => removeFilter('assets', asset.symbol)}
                    >
                      x
                    </span>
                  </Badge>
                ))}

                {filterState.selectedExchanges.size > 0 &&
                 filterState.selectedExchanges.size < ALL_EXCHANGES.length && (
                  <Badge
                    variant="outline"
                    className="gap-1.5 py-1 px-2.5 bg-background hover:bg-muted cursor-default"
                  >
                    <span>{filterState.selectedExchanges.size} Exchanges</span>
                    <span
                      className="inline-flex items-center justify-center w-3.5 h-3.5 bg-gray-500 hover:bg-gray-600 rounded-full text-white text-xs leading-none cursor-pointer"
                      onClick={() => removeFilter('exchanges')}
                    >
                      x
                    </span>
                  </Badge>
                )}

                {filterState.selectedIntervals.size > 0 &&
                 filterState.selectedIntervals.size < 4 && (
                  <Badge
                    variant="outline"
                    className="gap-1.5 py-1 px-2.5 bg-background hover:bg-muted cursor-default"
                  >
                    <span>{filterState.selectedIntervals.size} Intervals</span>
                    <span
                      className="inline-flex items-center justify-center w-3.5 h-3.5 bg-gray-500 hover:bg-gray-600 rounded-full text-white text-xs leading-none cursor-pointer"
                      onClick={() => removeFilter('intervals')}
                    >
                      x
                    </span>
                  </Badge>
                )}

                {(filterState.minApr !== null || filterState.maxApr !== null) && (
                  <Badge
                    variant="outline"
                    className="gap-1.5 py-1 px-2.5 bg-background hover:bg-muted cursor-default"
                  >
                    <span>
                      APR: {filterState.minApr !== null ? `>${filterState.minApr}%` : ''}
                      {filterState.minApr !== null && filterState.maxApr !== null ? ' - ' : ''}
                      {filterState.maxApr !== null ? `<${filterState.maxApr}%` : ''}
                    </span>
                    <span
                      className="inline-flex items-center justify-center w-3.5 h-3.5 bg-gray-500 hover:bg-gray-600 rounded-full text-white text-xs leading-none cursor-pointer"
                      onClick={() => removeFilter('apr')}
                    >
                      x
                    </span>
                  </Badge>
                )}

                {(filterState.minOIEither !== null || filterState.minOICombined !== null) && (
                  <Badge
                    variant="outline"
                    className="gap-1.5 py-1 px-2.5 bg-background hover:bg-muted cursor-default"
                  >
                    <span>Liquidity filters</span>
                    <span
                      className="inline-flex items-center justify-center w-3.5 h-3.5 bg-gray-500 hover:bg-gray-600 rounded-full text-white text-xs leading-none cursor-pointer"
                      onClick={() => removeFilter('liquidity')}
                    >
                      x
                    </span>
                  </Badge>
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
