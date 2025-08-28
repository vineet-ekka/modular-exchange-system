import React from 'react';

interface DataFetchingSettingsProps {
  settings: {
    enable_funding_rate: boolean;
    enable_open_interest: boolean;
    api_delay: number;
    display_limit: number;
    sort_column: string;
    sort_ascending: boolean;
  };
  historicalSettings: {
    enable_collection: boolean;
    fetch_interval: number;
    max_retries: number;
    base_backoff: number;
  };
  outputSettings: {
    enable_csv: boolean;
    enable_database: boolean;
    enable_console: boolean;
    csv_filename: string;
  };
  onChange: (settings: any) => void;
  onHistoricalChange: (settings: any) => void;
  onOutputChange: (settings: any) => void;
}

const DataFetchingSettings: React.FC<DataFetchingSettingsProps> = ({ 
  settings, 
  historicalSettings,
  outputSettings,
  onChange,
  onHistoricalChange,
  onOutputChange
}) => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-4">Data Collection Settings</h3>
        <p className="text-gray-400 mb-6">
          Configure how data is fetched from exchanges and processed.
        </p>
      </div>

      {/* Data Types */}
      <div>
        <h4 className="text-lg font-medium mb-3">Data Types</h4>
        <div className="space-y-3">
          <label className="flex items-center p-4 bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-600 transition-colors">
            <input
              type="checkbox"
              checked={settings.enable_funding_rate}
              onChange={(e) => onChange({ ...settings, enable_funding_rate: e.target.checked })}
              className="mr-3"
            />
            <div>
              <div className="font-medium">Funding Rates</div>
              <div className="text-sm text-gray-400">Collect current and historical funding rate data</div>
            </div>
          </label>
          
          <label className="flex items-center p-4 bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-600 transition-colors">
            <input
              type="checkbox"
              checked={settings.enable_open_interest}
              onChange={(e) => onChange({ ...settings, enable_open_interest: e.target.checked })}
              className="mr-3"
            />
            <div>
              <div className="font-medium">Open Interest</div>
              <div className="text-sm text-gray-400">Collect open interest data (may cause API errors on some exchanges)</div>
            </div>
          </label>
        </div>
      </div>

      {/* API Settings */}
      <div>
        <h4 className="text-lg font-medium mb-3">API Configuration</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-gray-700 rounded-lg">
            <label>
              <span className="text-sm text-gray-400">API Call Delay (seconds)</span>
              <div className="flex items-center mt-2">
                <input
                  type="number"
                  min="0"
                  max="10"
                  step="0.1"
                  value={settings.api_delay}
                  onChange={(e) => onChange({ ...settings, api_delay: Number(e.target.value) })}
                  className="w-full px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="text-xs text-gray-500 mt-1">Delay between API calls to avoid rate limiting</div>
            </label>
          </div>
          
          <div className="p-4 bg-gray-700 rounded-lg">
            <label>
              <span className="text-sm text-gray-400">Display Limit</span>
              <div className="flex items-center mt-2">
                <input
                  type="number"
                  min="10"
                  max="1000"
                  step="10"
                  value={settings.display_limit}
                  onChange={(e) => onChange({ ...settings, display_limit: Number(e.target.value) })}
                  className="w-full px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="text-xs text-gray-500 mt-1">Maximum results to display in tables</div>
            </label>
          </div>
        </div>
      </div>

      {/* Historical Collection */}
      <div>
        <h4 className="text-lg font-medium mb-3">Historical Data Collection</h4>
        <div className="space-y-4">
          <label className="flex items-center p-4 bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-600 transition-colors">
            <input
              type="checkbox"
              checked={historicalSettings.enable_collection}
              onChange={(e) => onHistoricalChange({ ...historicalSettings, enable_collection: e.target.checked })}
              className="mr-3"
            />
            <div>
              <div className="font-medium">Enable Historical Collection</div>
              <div className="text-sm text-gray-400">Continuously collect historical funding rate data</div>
            </div>
          </label>
          
          {historicalSettings.enable_collection && (
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-700 rounded-lg">
                <label>
                  <span className="text-sm text-gray-400">Fetch Interval (seconds)</span>
                  <input
                    type="number"
                    min="30"
                    max="3600"
                    step="30"
                    value={historicalSettings.fetch_interval}
                    onChange={(e) => onHistoricalChange({ ...historicalSettings, fetch_interval: Number(e.target.value) })}
                    className="w-full mt-2 px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                  />
                </label>
              </div>
              
              <div className="p-4 bg-gray-700 rounded-lg">
                <label>
                  <span className="text-sm text-gray-400">Max Retry Attempts</span>
                  <input
                    type="number"
                    min="0"
                    max="10"
                    value={historicalSettings.max_retries}
                    onChange={(e) => onHistoricalChange({ ...historicalSettings, max_retries: Number(e.target.value) })}
                    className="w-full mt-2 px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                  />
                </label>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Output Settings */}
      <div>
        <h4 className="text-lg font-medium mb-3">Output Configuration</h4>
        <div className="space-y-3">
          <label className="flex items-center p-4 bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-600 transition-colors">
            <input
              type="checkbox"
              checked={outputSettings.enable_database}
              onChange={(e) => onOutputChange({ ...outputSettings, enable_database: e.target.checked })}
              className="mr-3"
            />
            <div>
              <div className="font-medium">Database Upload</div>
              <div className="text-sm text-gray-400">Save data to PostgreSQL database</div>
            </div>
          </label>
          
          <label className="flex items-center p-4 bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-600 transition-colors">
            <input
              type="checkbox"
              checked={outputSettings.enable_console}
              onChange={(e) => onOutputChange({ ...outputSettings, enable_console: e.target.checked })}
              className="mr-3"
            />
            <div>
              <div className="font-medium">Console Display</div>
              <div className="text-sm text-gray-400">Show data in terminal/console output</div>
            </div>
          </label>
          
          <label className="flex items-center p-4 bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-600 transition-colors">
            <input
              type="checkbox"
              checked={outputSettings.enable_csv}
              onChange={(e) => onOutputChange({ ...outputSettings, enable_csv: e.target.checked })}
              className="mr-3"
            />
            <div>
              <div className="font-medium">CSV Export</div>
              <div className="text-sm text-gray-400">Export data to CSV files</div>
            </div>
          </label>
          
          {outputSettings.enable_csv && (
            <div className="p-4 bg-gray-700 rounded-lg ml-7">
              <label>
                <span className="text-sm text-gray-400">CSV Filename</span>
                <input
                  type="text"
                  value={outputSettings.csv_filename}
                  onChange={(e) => onOutputChange({ ...outputSettings, csv_filename: e.target.value })}
                  className="w-full mt-2 px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                />
              </label>
            </div>
          )}
        </div>
      </div>

      {/* Sorting Defaults */}
      <div>
        <h4 className="text-lg font-medium mb-3">Default Sorting</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-gray-700 rounded-lg">
            <label>
              <span className="text-sm text-gray-400">Sort Column</span>
              <select
                value={settings.sort_column}
                onChange={(e) => onChange({ ...settings, sort_column: e.target.value })}
                className="w-full mt-2 px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              >
                <option value="exchange">Exchange</option>
                <option value="symbol">Symbol</option>
                <option value="funding_rate">Funding Rate</option>
                <option value="apr">APR</option>
                <option value="mark_price">Mark Price</option>
                <option value="open_interest">Open Interest</option>
              </select>
            </label>
          </div>
          
          <div className="p-4 bg-gray-700 rounded-lg">
            <label>
              <span className="text-sm text-gray-400">Sort Direction</span>
              <select
                value={settings.sort_ascending ? 'asc' : 'desc'}
                onChange={(e) => onChange({ ...settings, sort_ascending: e.target.value === 'asc' })}
                className="w-full mt-2 px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              >
                <option value="asc">Ascending</option>
                <option value="desc">Descending</option>
              </select>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataFetchingSettings;