import React, { useState, useEffect, useMemo, useRef } from 'react';
import { debounce } from 'lodash';
import { Asset } from '../../types/arbitrageFilter';
import styles from './ArbitrageFilter.module.css';

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

  // Server-side search with debouncing
  const performSearch = async (query: string) => {
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

      // Filter out already selected assets
      const filtered = data.results.filter(
        (asset: Asset) => !selectedAssets.some(s => s.symbol === asset.symbol)
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
  };

  const debouncedSearch = useMemo(
    () => debounce(performSearch, 150),
    [selectedAssets]
  );

  useEffect(() => {
    debouncedSearch(searchQuery);
    return () => debouncedSearch.cancel();
  }, [searchQuery, debouncedSearch]);

  // Handle asset selection
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

  // Handle asset removal
  const handleRemoveAsset = (symbol: string) => {
    onChange(selectedAssets.filter(a => a.symbol !== symbol));
  };

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'Backspace' && !searchQuery && selectedAssets.length > 0) {
        // Remove last tag on backspace
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

  // Scroll highlighted item into view
  useEffect(() => {
    if (isOpen && dropdownRef.current) {
      const highlightedElement = dropdownRef.current.querySelector(
        `[data-index="${highlightedIndex}"]`
      );
      highlightedElement?.scrollIntoView({ block: 'nearest' });
    }
  }, [highlightedIndex, isOpen]);

  // Click outside handler
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
    <div className={styles.filterSection}>
      <div className={styles.sectionLabel}>Basic Filters</div>
      <div className={styles.inputGroup}>
        <label className={styles.inputLabel}>Asset</label>
        <div className={styles.assetAutocompleteWrapper}>
          <div
            className={styles.assetTagInput}
            onClick={() => inputRef.current?.focus()}
          >
            <div className={styles.assetTags}>
              {/* Selected asset tags */}
              {selectedAssets.map(asset => (
                <div key={asset.symbol} className={styles.assetTag}>
                  <span>{asset.symbol}</span>
                  <span
                    className={styles.tagRemove}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoveAsset(asset.symbol);
                    }}
                    aria-label={`Remove ${asset.symbol}`}
                  >
                    ×
                  </span>
                </div>
              ))}
            </div>

            {/* Search input */}
            <input
              ref={inputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={selectedAssets.length === 0 ? placeholder : ''}
              className={styles.assetSearchInput}
              role="combobox"
              aria-autocomplete="list"
              aria-controls="asset-autocomplete-list"
              aria-expanded={isOpen}
              aria-activedescendant={isOpen ? `asset-option-${highlightedIndex}` : undefined}
            />
          </div>

          {/* Autocomplete dropdown */}
          <div
            ref={dropdownRef}
            id="asset-autocomplete-list"
            role="listbox"
            className={`${styles.autocompleteDropdown} ${isOpen ? styles.visible : ''}`}
          >
            {loading ? (
              <div className={styles.autocompleteNoResults}>
                Searching...
              </div>
            ) : searchResults.length === 0 ? (
              <div className={styles.autocompleteNoResults}>
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
                  className={`${styles.autocompleteItem} ${
                    index === highlightedIndex ? styles.highlighted : ''
                  }`}
                  onClick={() => handleSelectAsset(asset)}
                >
                  <div className={styles.autocompleteSymbol}>
                    <span className={styles.autocompleteSymbolText}>{asset.symbol}</span>
                    <span className={styles.autocompleteSymbolName}>{asset.name}</span>
                  </div>
                  <div className={styles.autocompleteMeta}>
                    <span className={styles.autocompleteMetaItem}>
                      {asset.exchanges} exchanges
                    </span>
                    <span className={`${styles.autocompleteMetaItem} ${
                      asset.avg_spread_pct && asset.avg_spread_pct >= 0 ? styles.positive : styles.negative
                    }`}>
                      Avg: {asset.avg_spread_pct?.toFixed(3)}%
                    </span>
                    <span className={styles.autocompleteMetaItem}>
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