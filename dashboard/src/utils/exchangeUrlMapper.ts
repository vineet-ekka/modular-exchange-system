interface ExchangeUrlConfig {
  pattern: string;
  usesBaseAsset?: boolean;
  transformer?: (symbol: string, baseAsset?: string) => string;
}

const EXCHANGE_URL_CONFIGS: Record<string, ExchangeUrlConfig> = {
  binance: {
    pattern: 'https://www.binance.com/en/futures/{symbol}',
  },
  kucoin: {
    pattern: 'https://www.kucoin.com/futures/trade/{symbol}',
  },
  bybit: {
    pattern: 'https://www.bybit.com/trade/usdt/{symbol}',
  },
  mexc: {
    pattern: 'https://www.mexc.com/exchange/{symbol}',
  },
  backpack: {
    pattern: 'https://backpack.exchange/trade/{symbol}',
  },
  deribit: {
    pattern: 'https://www.deribit.com/{symbol}',
  },
  hyperliquid: {
    pattern: 'https://app.hyperliquid.xyz/trade/{symbol}',
    usesBaseAsset: true,
  },
  drift: {
    pattern: 'https://app.drift.trade/trade/{symbol}',
    usesBaseAsset: true,
    transformer: (symbol: string, baseAsset?: string) => {
      const asset = baseAsset || symbol;
      return asset.endsWith('-PERP') ? asset : `${asset}-PERP`;
    },
  },
  aster: {
    pattern: 'https://www.asterdex.com/en/futures/v1/{symbol}',
  },
  lighter: {
    pattern: 'https://app.lighter.xyz/trade/{symbol}',
    usesBaseAsset: true,
    transformer: (symbol: string, baseAsset?: string) => {
      return baseAsset || symbol.replace(/USDT$/, '');
    },
  },
  paradex: {
    pattern: 'https://app.paradex.trade/trade/{symbol}',
    usesBaseAsset: true,
    transformer: (symbol: string, baseAsset?: string) => {
      const asset = baseAsset || symbol.replace(/USDT$/, '');
      return `${asset}-USD-PERP`;
    },
  },
  orderly: {
    pattern: 'https://app.orderly.network/perp/{symbol}',
  },
  pacifica: {
    pattern: 'https://app.pacifica.fi/trade/{symbol}',
  },
  hibachi: {
    pattern: 'https://app.hibachi.finance/trade/{symbol}',
  },
  dydx: {
    pattern: 'https://trade.dydx.exchange/trade/{symbol}',
  },
};

export interface ContractUrlOptions {
  exchange: string;
  symbol: string;
  baseAsset?: string;
}

export function getContractTradingUrl(options: ContractUrlOptions): string | null {
  const { exchange, symbol, baseAsset } = options;

  const exchangeKey = exchange.toLowerCase();
  const config = EXCHANGE_URL_CONFIGS[exchangeKey];

  if (!config) {
    return null;
  }

  let finalSymbol: string;

  if (config.usesBaseAsset) {
    if (config.transformer) {
      finalSymbol = config.transformer(symbol, baseAsset);
    } else {
      finalSymbol = baseAsset || symbol;
    }
  } else {
    finalSymbol = config.transformer ? config.transformer(symbol, baseAsset) : symbol;
  }

  return config.pattern.replace('{symbol}', finalSymbol);
}

export function isExchangeSupported(exchange: string): boolean {
  return exchange.toLowerCase() in EXCHANGE_URL_CONFIGS;
}

export function getSupportedExchanges(): string[] {
  return Object.keys(EXCHANGE_URL_CONFIGS);
}
