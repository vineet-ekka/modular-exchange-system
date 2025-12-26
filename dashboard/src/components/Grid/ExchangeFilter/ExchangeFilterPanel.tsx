import React from 'react';
import { ExchangeFilterState } from '../../../types/exchangeFilter';
import { EXCHANGE_METADATA, ALL_EXCHANGES } from '../../../constants/exchangeMetadata';
import { DEFAULT_FILTER_STATE } from '../../../hooks/useFilterPersistence';
import { Button } from '../../ui/button';
import { Checkbox } from '../../ui/checkbox';
import { Label } from '../../ui/label';
import { Separator } from '../../ui/separator';
import { ScrollArea } from '../../ui/scroll-area';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '../../ui/sheet';

interface ExchangeFilterPanelProps {
  exchanges: string[];
  selectedExchanges: Set<string>;
  onExchangesChange: (selected: Set<string>) => void;
  filterState: ExchangeFilterState;
  onFilterStateChange: (state: Partial<ExchangeFilterState>) => void;
  size?: 'default' | 'compact';
}

const ExchangeFilterPanel: React.FC<ExchangeFilterPanelProps> = ({
  exchanges,
  selectedExchanges,
  onExchangesChange,
  filterState,
  onFilterStateChange,
  size = 'default',
}) => {
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

  const handleExchangeToggle = (exchange: string) => {
    const newSelected = new Set(selectedExchanges);
    if (newSelected.has(exchange)) {
      if (newSelected.size > 1) {
        newSelected.delete(exchange);
      }
    } else {
      newSelected.add(exchange);
    }
    onExchangesChange(newSelected);
  };

  const isFiltered = selectedExchanges.size < ALL_EXCHANGES.length ||
    filterState.hideEmptyAssets ||
    filterState.showOnlyCrossListed ||
    filterState.highlightMissing;

  const activeFilterCount = [
    selectedExchanges.size < ALL_EXCHANGES.length,
    filterState.hideEmptyAssets,
    filterState.showOnlyCrossListed,
    filterState.highlightMissing,
  ].filter(Boolean).length;

  const isCompact = size === 'compact';

  return (
    <div className={isCompact ? "mb-2" : "mb-3"}>
      <Sheet>
        <SheetTrigger asChild>
          <Button
            variant="outline"
            size={isCompact ? "sm" : "default"}
            className="w-full justify-between hover:bg-gray-100"
          >
            <span className="flex items-center gap-2">
              <span className="text-xs font-semibold text-text-primary">EXCHANGE FILTER</span>
              {isFiltered && (
                <span className="px-1.5 py-0.5 text-xs bg-sky-500/10 text-sky-600 border border-sky-500/20 rounded-full">
                  {activeFilterCount}
                </span>
              )}
            </span>
            <span className="text-xs text-text-tertiary">
              {selectedExchanges.size}/{exchanges.length}
            </span>
          </Button>
        </SheetTrigger>
        <SheetContent side="right" className="w-80 p-4">
          <SheetHeader>
            <SheetTitle className="text-sm font-semibold text-text-primary">Exchange Filters</SheetTitle>
            <SheetDescription className="text-xs text-text-tertiary">
              {selectedExchanges.size} of {exchanges.length} exchanges selected
            </SheetDescription>
          </SheetHeader>

          <div className="mt-4 space-y-4">
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
              <button
                onClick={handleReset}
                className={`px-2.5 py-1 text-xs font-medium text-sky-500 hover:text-sky-700 underline transition-colors ${isFiltered ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
              >
                Reset All
              </button>
            </div>

            <Separator className="bg-border" />

            <div>
              <h4 className="text-xs font-medium text-text-secondary mb-2">Exchanges</h4>
              <ScrollArea className="h-[240px] rounded-md border border-border p-2">
                <div className="space-y-1.5">
                  {exchanges.map((exchange) => {
                    const metadata = EXCHANGE_METADATA[exchange];
                    const isSelected = selectedExchanges.has(exchange);
                    const exchangeId = `exchange-${exchange}`;

                    return (
                      <div
                        key={exchange}
                        className="flex items-center justify-between"
                      >
                        <div className="flex items-center space-x-1.5">
                          <Checkbox
                            id={exchangeId}
                            checked={isSelected}
                            onCheckedChange={() => handleExchangeToggle(exchange)}
                            disabled={isSelected && selectedExchanges.size === 1}
                          />
                          <Label
                            htmlFor={exchangeId}
                            className="text-xs font-normal text-text-secondary cursor-pointer"
                          >
                            {exchange.charAt(0).toUpperCase() + exchange.slice(1)}
                          </Label>
                        </div>
                        <div className="flex items-center gap-1.5 w-[52px] justify-end">
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: metadata?.color || 'transparent' }}
                          />
                          <span className="text-xs px-1 py-0.5 bg-gray-100 text-gray-700 rounded min-w-[32px] text-right tabular-nums">
                            {metadata?.contracts || 0}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </ScrollArea>
            </div>

            <Separator className="bg-border" />

            <div className="space-y-2">
              <h4 className="text-xs font-medium text-text-secondary">Display Options</h4>

              <div className="flex items-center space-x-1.5">
                <Checkbox
                  id="hide-empty"
                  checked={filterState.hideEmptyAssets}
                  onCheckedChange={(checked) =>
                    onFilterStateChange({ hideEmptyAssets: checked === true })
                  }
                />
                <Label htmlFor="hide-empty" className="text-xs font-normal text-text-secondary cursor-pointer">
                  Hide empty assets
                </Label>
              </div>

              <div className="flex items-center space-x-1.5">
                <Checkbox
                  id="cross-listed"
                  checked={filterState.showOnlyCrossListed}
                  onCheckedChange={(checked) =>
                    onFilterStateChange({ showOnlyCrossListed: checked === true })
                  }
                />
                <Label htmlFor="cross-listed" className="text-xs font-normal text-text-secondary cursor-pointer">
                  Cross-listed only
                </Label>
              </div>

              <div className="flex items-center space-x-1.5">
                <Checkbox
                  id="highlight-missing"
                  checked={filterState.highlightMissing}
                  onCheckedChange={(checked) =>
                    onFilterStateChange({ highlightMissing: checked === true })
                  }
                />
                <Label htmlFor="highlight-missing" className="text-xs font-normal text-text-secondary cursor-pointer">
                  Highlight missing
                </Label>
              </div>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default ExchangeFilterPanel;
