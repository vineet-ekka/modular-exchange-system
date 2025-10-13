import { ExchangeMetadata } from '../types/exchangeFilter';

export const EXCHANGE_METADATA: Record<string, ExchangeMetadata> = {
  binance: {
    type: 'CEX',
    category: 'Major',
    contracts: 547,
    color: '#F3BA2F',
    funding_intervals: [1, 4, 8],
    orderPriority: 1
  },
  bybit: {
    type: 'CEX',
    category: 'Major',
    contracts: 696,
    color: '#F7A600',
    funding_intervals: [1, 2, 4, 8],
    orderPriority: 2
  },
  kucoin: {
    type: 'CEX',
    category: 'Major',
    contracts: 477,
    color: '#24AE8F',
    funding_intervals: [1, 2, 4, 8],
    orderPriority: 3
  },
  backpack: {
    type: 'CEX',
    category: 'Emerging',
    contracts: 43,
    color: '#E8421D',
    funding_intervals: [1],
    orderPriority: 4
  },
  hyperliquid: {
    type: 'DEX',
    category: 'Major',
    contracts: 173,
    color: '#00D4FF',
    funding_intervals: [1],
    orderPriority: 5
  },
  aster: {
    type: 'DEX',
    category: 'Emerging',
    contracts: 102,
    color: '#9F7AEA',
    funding_intervals: [4],
    orderPriority: 6
  },
  drift: {
    type: 'DEX',
    category: 'Emerging',
    contracts: 61,
    color: '#A78BFA',
    funding_intervals: [1],
    orderPriority: 7
  },
  lighter: {
    type: 'DEX',
    category: 'Emerging',
    contracts: 330,
    color: '#818CF8',
    funding_intervals: 'variable',
    orderPriority: 8
  },
  deribit: {
    type: 'CEX',
    category: 'Options',
    contracts: 0,
    color: '#3B3B3B',
    funding_intervals: [8],
    orderPriority: 99,
    disabled: true
  },
  kraken: {
    type: 'CEX',
    category: 'Major',
    contracts: 0,
    color: '#5741D9',
    funding_intervals: [4],
    orderPriority: 100,
    disabled: true
  }
};

export const ALL_EXCHANGES = Object.keys(EXCHANGE_METADATA)
  .filter(ex => !EXCHANGE_METADATA[ex].disabled)
  .sort((a, b) => EXCHANGE_METADATA[a].orderPriority - EXCHANGE_METADATA[b].orderPriority);

export const CEX_EXCHANGES = ALL_EXCHANGES.filter(
  ex => EXCHANGE_METADATA[ex].type === 'CEX'
);

export const DEX_EXCHANGES = ALL_EXCHANGES.filter(
  ex => EXCHANGE_METADATA[ex].type === 'DEX'
);

export const MAJOR_EXCHANGES = ALL_EXCHANGES.filter(
  ex => EXCHANGE_METADATA[ex].category === 'Major'
);

export const HOURLY_FUNDING_EXCHANGES = ALL_EXCHANGES.filter(
  ex => {
    const intervals = EXCHANGE_METADATA[ex].funding_intervals;
    return Array.isArray(intervals) && intervals.includes(1);
  }
);
