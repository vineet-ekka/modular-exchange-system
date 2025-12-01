import { AssetGridData } from '../types/exchangeFilter';
import { ContractDetails } from '../services/api';

export type SearchIndex = Map<string, Set<string>>;

export const getVisibleExchanges = (
  allExchanges: string[],
  selectedExchanges: Set<string>
): string[] => {
  const visible = allExchanges.filter(ex => selectedExchanges.has(ex));
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

export function createSearchIndex(
  assets: AssetGridData[],
  contracts: Record<string, ContractDetails[]>
): SearchIndex {
  const index = new Map<string, Set<string>>();

  assets.forEach((asset) => {
    const searchTerms = new Set<string>();
    searchTerms.add(asset.asset.toLowerCase());

    const assetContracts = contracts[asset.asset] || [];
    assetContracts.forEach((contract) => {
      searchTerms.add(contract.symbol.toLowerCase());
    });

    index.set(asset.asset, searchTerms);
  });

  return index;
}

export function searchWithIndex(
  searchTerm: string,
  assets: AssetGridData[],
  index: SearchIndex
): AssetGridData[] {
  if (!searchTerm || searchTerm.length < 2) return assets;

  const searchLower = searchTerm.toLowerCase();

  return assets.filter((asset) => {
    const terms = index.get(asset.asset);
    if (!terms) return false;
    return Array.from(terms).some((term) => term.includes(searchLower));
  });
}
