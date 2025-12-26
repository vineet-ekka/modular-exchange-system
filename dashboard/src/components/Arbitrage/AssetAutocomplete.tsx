import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import debounce from 'lodash/debounce';
import { Asset } from '../../types/arbitrageFilter';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { cn } from '@/lib/utils';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface AssetAutocompleteProps {
  selectedAssets: Asset[];
  onChange: (assets: Asset[]) => void;
  placeholder?: string;
  maxSelections?: number;
}

export const AssetAutocomplete: React.FC<AssetAutocompleteProps> = ({
  selectedAssets,
  onChange,
  placeholder = "Search assets (e.g., BTC, ETH, SOL)",
  maxSelections = 20
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Asset[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedAssetsRef = useRef(selectedAssets);
  selectedAssetsRef.current = selectedAssets;

  const performSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setIsOpen(false);
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `${API_URL}/api/arbitrage/assets/search?q=${encodeURIComponent(query)}&limit=10`
      );
      const data = await response.json();

      const filtered = data.results.filter(
        (asset: Asset) => !selectedAssetsRef.current.some(s => s.symbol === asset.symbol)
      );

      setSearchResults(filtered);
      setIsOpen(filtered.length > 0);
      setHighlightedIndex(0);
    } catch (error) {
      console.error('Asset search failed:', error);
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const debouncedSearch = useMemo(
    () => debounce(performSearch, 150),
    [performSearch]
  );

  useEffect(() => {
    debouncedSearch(searchQuery);
    return () => debouncedSearch.cancel();
  }, [searchQuery, debouncedSearch]);

  const handleSelectAsset = (asset: Asset) => {
    if (selectedAssets.length >= maxSelections) {
      alert(`Maximum ${maxSelections} assets allowed`);
      return;
    }

    onChange([...selectedAssets, asset]);
    setSearchQuery('');
    setSearchResults([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  const handleRemoveAsset = (symbol: string) => {
    onChange(selectedAssets.filter(a => a.symbol !== symbol));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'Backspace' && !searchQuery && selectedAssets.length > 0) {
        handleRemoveAsset(selectedAssets[selectedAssets.length - 1].symbol);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev =>
          Math.min(prev + 1, searchResults.length - 1)
        );
        break;

      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => Math.max(prev - 1, 0));
        break;

      case 'Enter':
        e.preventDefault();
        if (searchResults[highlightedIndex]) {
          handleSelectAsset(searchResults[highlightedIndex]);
        }
        break;

      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        setSearchQuery('');
        break;
    }
  };

  useEffect(() => {
    if (isOpen && dropdownRef.current) {
      const highlightedElement = dropdownRef.current.querySelector(
        `[data-index="${highlightedIndex}"]`
      );
      highlightedElement?.scrollIntoView({ block: 'nearest' });
    }
  }, [highlightedIndex, isOpen]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        inputRef.current &&
        !inputRef.current.contains(e.target as Node) &&
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="mb-6 last:mb-0">
      <div className="text-muted-foreground text-xs font-semibold uppercase tracking-wider mb-3">
        Basic Filters
      </div>
      <div className="space-y-1.5">
        <Label className="text-muted-foreground text-sm font-medium">Asset</Label>
        <div className="relative">
          <div
            className="w-full min-h-[38px] p-1 px-2 bg-background border border-input rounded-md flex flex-wrap gap-1.5 items-center cursor-text transition-all hover:border-gray-300 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/10"
            onClick={() => inputRef.current?.focus()}
          >
            <div className="flex flex-wrap gap-1.5">
              {selectedAssets.map(asset => (
                <Badge
                  key={asset.symbol}
                  variant="info"
                  className="gap-1.5 py-1 px-2 rounded-full"
                >
                  <span>{asset.symbol}</span>
                  <span
                    className="inline-flex items-center justify-center w-3.5 h-3.5 bg-blue-500 hover:bg-blue-600 rounded-full text-white text-xs leading-none cursor-pointer"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoveAsset(asset.symbol);
                    }}
                    aria-label={`Remove ${asset.symbol}`}
                  >
                    x
                  </span>
                </Badge>
              ))}
            </div>

            <input
              ref={inputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={selectedAssets.length === 0 ? placeholder : ''}
              className="flex-1 min-w-[120px] border-none outline-none p-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground"
              role="combobox"
              aria-autocomplete="list"
              aria-controls="asset-autocomplete-list"
              aria-expanded={isOpen}
              aria-activedescendant={isOpen ? `asset-option-${highlightedIndex}` : undefined}
            />
          </div>

          <div
            ref={dropdownRef}
            id="asset-autocomplete-list"
            role="listbox"
            className={cn(
              "absolute top-full left-0 right-0 mt-1 max-h-[320px] bg-popover border border-border rounded-md shadow-lg overflow-y-auto z-50",
              isOpen ? "block" : "hidden"
            )}
          >
            {loading ? (
              <div className="p-5 text-center text-muted-foreground text-sm">
                Searching...
              </div>
            ) : searchResults.length === 0 ? (
              <div className="p-5 text-center text-muted-foreground text-sm">
                No assets found
              </div>
            ) : (
              searchResults.map((asset, index) => (
                <div
                  key={asset.symbol}
                  data-index={index}
                  role="option"
                  id={`asset-option-${index}`}
                  aria-selected={index === highlightedIndex}
                  className={cn(
                    "p-2.5 px-3 cursor-pointer transition-all border-b border-border last:border-b-0",
                    index === highlightedIndex
                      ? "bg-muted"
                      : "hover:bg-muted/50"
                  )}
                  onClick={() => handleSelectAsset(asset)}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-semibold text-foreground">{asset.symbol}</span>
                    <span className="text-xs text-muted-foreground">{asset.name}</span>
                  </div>
                  <div className="flex gap-3 text-xs">
                    <span className="text-muted-foreground">
                      {asset.exchanges} exchanges
                    </span>
                    <span className={cn(
                      asset.avg_spread_pct && asset.avg_spread_pct >= 0
                        ? "text-success"
                        : "text-destructive"
                    )}>
                      Avg: {asset.avg_spread_pct?.toFixed(3)}%
                    </span>
                    <span className="text-muted-foreground">
                      {asset.total_opportunities} opps
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AssetAutocomplete;
