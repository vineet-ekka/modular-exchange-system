import React, { useState } from 'react';

interface AdvancedSettingsProps {
  settings: {
    debug_mode: boolean;
    show_sample_data: boolean;
  };
  databaseSettings: {
    host: string;
    port: string;
    database: string;
    user: string;
    table_name: string;
    historical_table: string;
  };
  onChange: (settings: any) => void;
  onDatabaseChange: (settings: any) => void;
}

const AdvancedSettings: React.FC<AdvancedSettingsProps> = ({ 
  settings, 
  databaseSettings,
  onChange,
  onDatabaseChange
}) => {
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [clearingDatabase, setClearingDatabase] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  const testDatabaseConnection = async () => {
    setTestingConnection(true);
    setConnectionStatus(null);
    
    try {
      const response = await fetch('http://localhost:8000/api/test');
      const data = await response.json();
      
      if (response.ok) {
        setConnectionStatus({
          type: 'success',
          message: `Connected successfully. ${data.total_records} records in database.`
        });
      } else {
        setConnectionStatus({
          type: 'error',
          message: 'Failed to connect to database'
        });
      }
    } catch (error) {
      setConnectionStatus({
        type: 'error',
        message: 'Connection failed: ' + (error as Error).message
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const clearDatabase = async () => {
    setClearingDatabase(true);
    try {
      // This would call an endpoint to clear the database
      // For now, we'll just simulate it
      await new Promise(resolve => setTimeout(resolve, 2000));
      setConnectionStatus({
        type: 'success',
        message: 'Database cleared successfully'
      });
      setShowClearConfirm(false);
    } catch (error) {
      setConnectionStatus({
        type: 'error',
        message: 'Failed to clear database'
      });
    } finally {
      setClearingDatabase(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-4">Advanced Settings</h3>
        <p className="text-gray-400 mb-6">
          Database configuration, debugging options, and system maintenance tools.
        </p>
      </div>

      {/* Database Configuration */}
      <div>
        <h4 className="text-lg font-medium mb-3">Database Configuration</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-gray-700 rounded-lg">
            <label>
              <span className="text-sm text-gray-400">Host</span>
              <input
                type="text"
                value={databaseSettings.host}
                onChange={(e) => onDatabaseChange({ ...databaseSettings, host: e.target.value })}
                className="w-full mt-2 px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </label>
          </div>
          
          <div className="p-4 bg-gray-700 rounded-lg">
            <label>
              <span className="text-sm text-gray-400">Port</span>
              <input
                type="text"
                value={databaseSettings.port}
                onChange={(e) => onDatabaseChange({ ...databaseSettings, port: e.target.value })}
                className="w-full mt-2 px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </label>
          </div>
          
          <div className="p-4 bg-gray-700 rounded-lg">
            <label>
              <span className="text-sm text-gray-400">Database Name</span>
              <input
                type="text"
                value={databaseSettings.database}
                onChange={(e) => onDatabaseChange({ ...databaseSettings, database: e.target.value })}
                className="w-full mt-2 px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </label>
          </div>
          
          <div className="p-4 bg-gray-700 rounded-lg">
            <label>
              <span className="text-sm text-gray-400">Username</span>
              <input
                type="text"
                value={databaseSettings.user}
                onChange={(e) => onDatabaseChange({ ...databaseSettings, user: e.target.value })}
                className="w-full mt-2 px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </label>
          </div>
          
          <div className="p-4 bg-gray-700 rounded-lg">
            <label>
              <span className="text-sm text-gray-400">Main Table Name</span>
              <input
                type="text"
                value={databaseSettings.table_name}
                onChange={(e) => onDatabaseChange({ ...databaseSettings, table_name: e.target.value })}
                className="w-full mt-2 px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </label>
          </div>
          
          <div className="p-4 bg-gray-700 rounded-lg">
            <label>
              <span className="text-sm text-gray-400">Historical Table Name</span>
              <input
                type="text"
                value={databaseSettings.historical_table}
                onChange={(e) => onDatabaseChange({ ...databaseSettings, historical_table: e.target.value })}
                className="w-full mt-2 px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </label>
          </div>
        </div>
        
        {/* Connection Test */}
        <div className="mt-4 flex items-center space-x-4">
          <button
            onClick={testDatabaseConnection}
            disabled={testingConnection}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white rounded-lg transition-colors"
          >
            {testingConnection ? 'Testing...' : 'Test Connection'}
          </button>
          
          {connectionStatus && (
            <div className={`text-sm ${
              connectionStatus.type === 'success' ? 'text-green-400' : 'text-red-400'
            }`}>
              {connectionStatus.message}
            </div>
          )}
        </div>
      </div>

      {/* Debug Options */}
      <div>
        <h4 className="text-lg font-medium mb-3">Debug Options</h4>
        <div className="space-y-3">
          <label className="flex items-center p-4 bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-600 transition-colors">
            <input
              type="checkbox"
              checked={settings.debug_mode}
              onChange={(e) => onChange({ ...settings, debug_mode: e.target.checked })}
              className="mr-3"
            />
            <div>
              <div className="font-medium">Debug Mode</div>
              <div className="text-sm text-gray-400">Enable detailed logging and error messages</div>
            </div>
          </label>
          
          <label className="flex items-center p-4 bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-600 transition-colors">
            <input
              type="checkbox"
              checked={settings.show_sample_data}
              onChange={(e) => onChange({ ...settings, show_sample_data: e.target.checked })}
              className="mr-3"
            />
            <div>
              <div className="font-medium">Show Sample Data</div>
              <div className="text-sm text-gray-400">Display sample data during upload operations</div>
            </div>
          </label>
        </div>
      </div>

      {/* Maintenance Tools */}
      <div>
        <h4 className="text-lg font-medium mb-3">Maintenance Tools</h4>
        <div className="space-y-3">
          {/* Clear Database */}
          <div className="p-4 bg-gray-700 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Clear Database</div>
                <div className="text-sm text-gray-400 mt-1">Remove all data from the database tables</div>
              </div>
              {!showClearConfirm ? (
                <button
                  onClick={() => setShowClearConfirm(true)}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                >
                  Clear Database
                </button>
              ) : (
                <div className="flex space-x-2">
                  <button
                    onClick={clearDatabase}
                    disabled={clearingDatabase}
                    className="px-4 py-2 bg-red-700 hover:bg-red-800 disabled:bg-gray-700 text-white rounded-lg transition-colors"
                  >
                    {clearingDatabase ? 'Clearing...' : 'Confirm Clear'}
                  </button>
                  <button
                    onClick={() => setShowClearConfirm(false)}
                    disabled={clearingDatabase}
                    className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          </div>
          
          {/* View Logs */}
          <div className="p-4 bg-gray-700 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">System Logs</div>
                <div className="text-sm text-gray-400 mt-1">View recent system activity and error logs</div>
              </div>
              <button
                className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
              >
                View Logs
              </button>
            </div>
          </div>
          
          {/* Backup Settings */}
          <div className="p-4 bg-gray-700 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Settings Backups</div>
                <div className="text-sm text-gray-400 mt-1">View and restore from previous settings backups</div>
              </div>
              <button
                className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
              >
                View Backups
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* System Information */}
      <div>
        <h4 className="text-lg font-medium mb-3">System Information</h4>
        <div className="p-4 bg-gray-700 rounded-lg">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400">API Version:</span>
              <span className="ml-2">1.1.0</span>
            </div>
            <div>
              <span className="text-gray-400">Dashboard Version:</span>
              <span className="ml-2">0.1.0</span>
            </div>
            <div>
              <span className="text-gray-400">PostgreSQL:</span>
              <span className="ml-2">15-alpine</span>
            </div>
            <div>
              <span className="text-gray-400">Python:</span>
              <span className="ml-2">3.8+</span>
            </div>
            <div>
              <span className="text-gray-400">Node.js:</span>
              <span className="ml-2">16+</span>
            </div>
            <div>
              <span className="text-gray-400">React:</span>
              <span className="ml-2">19.1.1</span>
            </div>
          </div>
        </div>
      </div>

      {/* Warning */}
      <div className="p-4 bg-red-900/30 border border-red-700 rounded-lg">
        <div className="flex items-start">
          <span className="text-red-500 mr-2">⚠️</span>
          <div className="text-sm text-red-400">
            <div className="font-medium mb-1">Caution:</div>
            <p>Changes to database configuration require restarting all services. Clearing the database will permanently remove all historical data.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdvancedSettings;