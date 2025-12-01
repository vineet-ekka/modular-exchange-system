import { useMemo, useRef, useEffect } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { createColumns, ColumnContext } from './columns';
import { AssetGridData, ViewMode } from './types';

class LRUCache<K, V> {
  private cache: Map<K, { value: V; timestamp: number }>;
  private maxSize: number;

  constructor(maxSize: number = 50) {
    this.cache = new Map();
    this.maxSize = maxSize;
  }

  get(key: K): V | undefined {
    const entry = this.cache.get(key);
    if (entry) {
      this.cache.delete(key);
      this.cache.set(key, { ...entry, timestamp: Date.now() });
      return entry.value;
    }
    return undefined;
  }

  set(key: K, value: V): void {
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value;
      if (firstKey !== undefined) {
        this.cache.delete(firstKey);
      }
    }
    this.cache.set(key, { value, timestamp: Date.now() });
  }

  getStats() {
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
    };
  }

  clear() {
    this.cache.clear();
  }
}

function getCacheKey(
  exchanges: string[],
  viewMode: ViewMode,
  highlightMissing: boolean
): string {
  const sortedExchanges = [...exchanges].sort().join(',');
  return `${sortedExchanges}_${viewMode}_${highlightMissing}`;
}

export function useColumns(
  visibleExchanges: string[],
  viewMode: ViewMode,
  highlightMissing: boolean
): ColumnDef<AssetGridData>[] {
  const cacheRef = useRef(new LRUCache<string, ColumnDef<AssetGridData>[]>(50));

  useEffect(() => {
    return () => {
      cacheRef.current.clear();
    };
  }, []);

  return useMemo(() => {
    const cacheKey = getCacheKey(visibleExchanges, viewMode, highlightMissing);
    const cached = cacheRef.current.get(cacheKey);

    if (cached) {
      return cached;
    }

    const newColumns = createColumns(visibleExchanges, {
      viewMode,
      highlightMissing,
    });

    cacheRef.current.set(cacheKey, newColumns);
    return newColumns;
  }, [visibleExchanges, viewMode, highlightMissing]);
}
