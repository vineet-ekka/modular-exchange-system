import { ExchangeMetadata } from '../types/exchangeFilter';

export const EXCHANGE_METADATA: Record<string, ExchangeMetadata> = {
  binance: {
    type: 'CEX',
    category: 'Major',
    contracts: 592,
    color: '#F3BA2F',
    funding_intervals: [1, 4, 8],
    orderPriority: 1
  },
  bybit: {
    type: 'CEX',
    category: 'Major',
    contracts: 667,
    color: '#F7A600',
    funding_intervals: [1, 2, 4, 8],
    orderPriority: 2
  },
  kucoin: {
    type: 'CEX',
    category: 'Major',
    contracts: 522,
    color: '#24AE8F',
    funding_intervals: [1, 2, 4, 8],
    orderPriority: 3
  },
  backpack: {
    type: 'CEX',
    category: 'Emerging',
    contracts: 63,
    color: '#E8421D',
    funding_intervals: [1],
    orderPriority: 4
  },
  hyperliquid: {
    type: 'DEX',
    category: 'Major',
    contracts: 182,
    color: '#00D4FF',
    funding_intervals: [1],
    orderPriority: 5
  },
  aster: {
    type: 'DEX',
    category: 'Emerging',
    contracts: 123,
    color: '#9F7AEA',
    funding_intervals: [4],
    orderPriority: 6
  },
  drift: {
    type: 'DEX',
    category: 'Emerging',
    contracts: 51,
    color: '#A78BFA',
    funding_intervals: [1],
    orderPriority: 7
  },
  lighter: {
    type: 'DEX',
    category: 'Emerging',
    contracts: 91,
    color: '#818CF8',
    funding_intervals: 'variable',
    orderPriority: 8
  },
  pacifica: {
    type: 'DEX',
    category: 'Emerging',
    contracts: 25,
    color: '#10B981',
    funding_intervals: [1],
    orderPriority: 9
  },
  paradex: {
    type: 'DEX',
    category: 'Emerging',
    contracts: 122,
    color: '#8B5CF6',
    funding_intervals: [1, 2, 4, 8],
    orderPriority: 10
  },
  deribit: {
    type: 'CEX',
    category: 'Options',
    contracts: 20,
    color: '#3B3B3B',
    funding_intervals: [8],
    orderPriority: 11
  },
  orderly: {
    type: 'DEX',
    category: 'Major',
    contracts: 139,
    color: '#00D4AA',
    funding_intervals: [8],
    orderPriority: 12
  },
  hibachi: {
    type: 'DEX',
    category: 'Emerging',
    contracts: 20,
    color: '#FF6B6B',
    funding_intervals: [8],
    orderPriority: 13
  },
  mexc: {
    type: 'CEX',
    category: 'Major',
    contracts: 826,
    color: '#00D4FF',
    funding_intervals: [8],
    orderPriority: 14
  },
  dydx: {
    type: 'DEX',
    category: 'Major',
    contracts: 199,
    color: '#6B46C1',
    funding_intervals: [8],
    orderPriority: 15
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
