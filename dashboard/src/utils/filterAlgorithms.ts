import { AssetGridData } from '../types/exchangeFilter';

export const getVisibleExchanges = (
  allExchanges: string[],
  selectedExchanges: Set<string>
): string[] => {
  const visible = allExchanges.filter(ex => selectedExchanges.has(ex));
  console.log('[VISIBLE] allExchanges:', allExchanges.length, allExchanges);
  console.log('[VISIBLE] selectedExchanges:', selectedExchanges.size, [...selectedExchanges].sort());
  console.log('[VISIBLE] visibleExchanges:', visible.length, visible);
  return visible;
};

export const filterAssetsByEmptyData = (
  assets: AssetGridData[],
  selectedExchanges: Set<string>
): AssetGridData[] => {
  return assets.filter(asset => {
    return Array.from(selectedExchanges).some(exchange => {
      const rate = asset.exchanges[exchange]?.funding_rate;
      return rate !== null && rate !== undefined;
    });
  });
};

export const filterAssetsByCrossListed = (
  assets: AssetGridData[],
  selectedExchanges: Set<string>
): AssetGridData[] => {
  if (selectedExchanges.size < 2) {
    return assets;
  }

  return assets.filter(asset => {
    return Array.from(selectedExchanges).every(exchange => {
      const rate = asset.exchanges[exchange]?.funding_rate;
      return rate !== null && rate !== undefined;
    });
  });
};
