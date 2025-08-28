import React from 'react';

interface ExchangeSettingsProps {
  settings: {
    enabled: Record<string, boolean>;
    collection_mode: 'sequential' | 'parallel';
    collection_delay: number;
  };
  onChange: (settings: any) => void;
}

const ExchangeSettings: React.FC<ExchangeSettingsProps> = ({ settings, onChange }) => {
  const exchanges = [
    { id: 'binance', name: 'Binance', contracts: 541, status: 'active' },
    { id: 'kucoin', name: 'KuCoin', contracts: 472, status: 'active' },
    { id: 'kraken', name: 'Kraken', contracts: 353, status: 'ready' },
    { id: 'deribit', name: 'Deribit', contracts: 20, status: 'ready' },
    { id: 'backpack', name: 'Backpack', contracts: 39, status: 'ready' }
  ];

  const handleExchangeToggle = (exchangeId: string) => {
    onChange({
      ...settings,
      enabled: {
        ...settings.enabled,
        [exchangeId]: !settings.enabled[exchangeId]
      }
    });
  };

  const handleModeChange = (mode: 'sequential' | 'parallel') => {
    onChange({
      ...settings,
      collection_mode: mode
    });
  };

  const handleDelayChange = (delay: number) => {
    onChange({
      ...settings,
      collection_delay: delay
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-4">Exchange Configuration</h3>
        <p className="text-gray-400 mb-6">
          Enable or disable exchanges for data collection. Sequential mode staggers API calls to reduce load.
        </p>
      </div>

      {/* Exchange List */}
      <div>
        <h4 className="text-lg font-medium mb-3">Active Exchanges</h4>
        <div className="space-y-3">
          {exchanges.map(exchange => (
            <div
              key={exchange.id}
              className="flex items-center justify-between p-4 bg-gray-700 rounded-lg"
            >
              <div className="flex items-center space-x-4">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.enabled[exchange.id] || false}
                    onChange={() => handleExchangeToggle(exchange.id)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
                <div>
                  <div className="font-medium">{exchange.name}</div>
                  <div className="text-sm text-gray-400">
                    {exchange.contracts} contracts
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <span className={`px-2 py-1 text-xs rounded ${
                  exchange.status === 'active' 
                    ? 'bg-green-900/50 text-green-400' 
                    : 'bg-yellow-900/50 text-yellow-400'
                }`}>
                  {exchange.status}
                </span>
                {settings.enabled[exchange.id] && (
                  <button className="px-3 py-1 text-sm bg-gray-600 hover:bg-gray-500 rounded transition-colors">
                    Test Connection
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Collection Mode */}
      <div>
        <h4 className="text-lg font-medium mb-3">Collection Mode</h4>
        <div className="space-y-3">
          <label className="flex items-start p-4 bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-600 transition-colors">
            <input
              type="radio"
              name="collection_mode"
              value="sequential"
              checked={settings.collection_mode === 'sequential'}
              onChange={() => handleModeChange('sequential')}
              className="mt-1 mr-3"
            />
            <div>
              <div className="font-medium">Sequential Collection</div>
              <div className="text-sm text-gray-400 mt-1">
                Staggers API calls to each exchange with a configurable delay. Reduces server load and API rate limit issues.
              </div>
            </div>
          </label>
          
          <label className="flex items-start p-4 bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-600 transition-colors">
            <input
              type="radio"
              name="collection_mode"
              value="parallel"
              checked={settings.collection_mode === 'parallel'}
              onChange={() => handleModeChange('parallel')}
              className="mt-1 mr-3"
            />
            <div>
              <div className="font-medium">Parallel Collection</div>
              <div className="text-sm text-gray-400 mt-1">
                Fetches data from all exchanges simultaneously. Faster updates but higher API load.
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* Collection Delay (only for sequential mode) */}
      {settings.collection_mode === 'sequential' && (
        <div>
          <h4 className="text-lg font-medium mb-3">Collection Delay</h4>
          <div className="p-4 bg-gray-700 rounded-lg">
            <div className="flex items-center space-x-4">
              <label className="flex-1">
                <span className="text-sm text-gray-400">Delay between exchanges (seconds)</span>
                <input
                  type="range"
                  min="0"
                  max="120"
                  step="5"
                  value={settings.collection_delay}
                  onChange={(e) => handleDelayChange(Number(e.target.value))}
                  className="w-full mt-2"
                />
              </label>
              <div className="text-2xl font-mono text-blue-400 min-w-[80px] text-right">
                {settings.collection_delay}s
              </div>
            </div>
            <div className="mt-3 text-sm text-gray-400">
              Time to wait between fetching data from different exchanges. 
              Example: Binance at 0s, KuCoin at {settings.collection_delay}s, Kraken at {settings.collection_delay * 2}s
            </div>
          </div>
        </div>
      )}

      {/* Summary */}
      <div className="p-4 bg-blue-900/30 border border-blue-700 rounded-lg">
        <div className="text-sm">
          <div className="font-medium text-blue-400 mb-2">Current Configuration:</div>
          <ul className="space-y-1 text-gray-300">
            <li>• {Object.values(settings.enabled).filter(Boolean).length} exchanges enabled</li>
            <li>• Mode: {settings.collection_mode === 'sequential' ? 'Sequential' : 'Parallel'} collection</li>
            {settings.collection_mode === 'sequential' && (
              <li>• Delay: {settings.collection_delay} seconds between exchanges</li>
            )}
            <li>• Total contracts: {
              exchanges
                .filter(e => settings.enabled[e.id])
                .reduce((sum, e) => sum + e.contracts, 0)
            }</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ExchangeSettings;