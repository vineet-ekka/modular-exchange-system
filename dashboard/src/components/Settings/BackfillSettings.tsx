import React, { useState, useEffect } from 'react';

interface BackfillStatus {
  status: string;
  message: string;
  progress?: number;
  total_records?: number;
  exchanges?: Record<string, any>;
}

const BackfillSettings: React.FC = () => {
  const [backfillStatus, setBackfillStatus] = useState<BackfillStatus | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [settings, setSettings] = useState({
    days: 30,
    exchanges: ['binance', 'kucoin'],
    batch_size: 10,
    parallel: true
  });
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  // Check backfill status periodically
  useEffect(() => {
    checkBackfillStatus();
    const interval = setInterval(checkBackfillStatus, 5000); // Check every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const checkBackfillStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/backfill/status');
      const data = await response.json();
      if (data.status === 'success' && data.backfill) {
        setBackfillStatus(data.backfill);
        setIsRunning(data.backfill.status === 'running');
      }
    } catch (error) {
      console.error('Error checking backfill status:', error);
    }
  };

  const startBackfill = async () => {
    setMessage(null);
    try {
      const response = await fetch('http://localhost:8000/api/backfill/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      
      const data = await response.json();
      
      if (response.ok && data.status === 'success') {
        setMessage({ type: 'success', text: data.message });
        setIsRunning(true);
        setTimeout(checkBackfillStatus, 1000); // Check status after 1 second
      } else {
        setMessage({ type: 'error', text: data.message || 'Failed to start backfill' });
      }
    } catch (error) {
      console.error('Error starting backfill:', error);
      setMessage({ type: 'error', text: 'Failed to start backfill operation' });
    }
  };

  const stopBackfill = async () => {
    setMessage(null);
    try {
      const response = await fetch('http://localhost:8000/api/backfill/stop', {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (response.ok && data.status === 'success') {
        setMessage({ type: 'success', text: data.message });
        setIsRunning(false);
        setTimeout(checkBackfillStatus, 1000);
      } else {
        setMessage({ type: 'error', text: 'Failed to stop backfill' });
      }
    } catch (error) {
      console.error('Error stopping backfill:', error);
      setMessage({ type: 'error', text: 'Failed to stop backfill operation' });
    }
  };

  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-4">Historical Data Backfill</h3>
        <p className="text-gray-400 mb-6">
          Backfill historical funding rate data from exchanges. This process may take several minutes to hours depending on the selected range.
        </p>
      </div>

      {/* Current Status */}
      {backfillStatus && backfillStatus.status !== 'idle' && (
        <div className="p-4 bg-gray-700 rounded-lg">
          <h4 className="text-lg font-medium mb-3">Current Backfill Status</h4>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Status:</span>
              <span className={`px-2 py-1 rounded text-sm ${
                backfillStatus.status === 'running' ? 'bg-blue-900/50 text-blue-400' :
                backfillStatus.status === 'completed' ? 'bg-green-900/50 text-green-400' :
                backfillStatus.status === 'error' ? 'bg-red-900/50 text-red-400' :
                'bg-gray-600 text-gray-300'
              }`}>
                {backfillStatus.status}
              </span>
            </div>
            
            {backfillStatus.message && (
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Message:</span>
                <span className="text-sm">{backfillStatus.message}</span>
              </div>
            )}
            
            {backfillStatus.progress !== undefined && (
              <div className="mt-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-gray-400">Progress:</span>
                  <span className="text-sm">{backfillStatus.progress}%</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${backfillStatus.progress}%` }}
                  />
                </div>
              </div>
            )}
            
            {backfillStatus.total_records && (
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Records Collected:</span>
                <span className="text-sm">{backfillStatus.total_records.toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Message */}
      {message && (
        <div className={`p-4 rounded-lg ${
          message.type === 'success' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
        }`}>
          {message.text}
        </div>
      )}

      {/* Backfill Settings */}
      <div className="space-y-4">
        <h4 className="text-lg font-medium">Backfill Configuration</h4>
        
        {/* Days to Backfill */}
        <div className="p-4 bg-gray-700 rounded-lg">
          <label>
            <span className="text-sm text-gray-400">Days to Backfill</span>
            <div className="flex items-center mt-2 space-x-4">
              <input
                type="range"
                min="1"
                max="90"
                value={settings.days}
                onChange={(e) => setSettings({ ...settings, days: Number(e.target.value) })}
                disabled={isRunning}
                className="flex-1"
              />
              <div className="text-2xl font-mono text-blue-400 min-w-[80px] text-right">
                {settings.days}
              </div>
            </div>
            <div className="text-xs text-gray-500 mt-2">
              Estimated time: {formatTime(settings.days * 10)} (varies by exchange and network speed)
            </div>
          </label>
        </div>

        {/* Exchanges Selection */}
        <div className="p-4 bg-gray-700 rounded-lg">
          <span className="text-sm text-gray-400 block mb-3">Exchanges to Backfill</span>
          <div className="space-y-2">
            {['binance', 'kucoin'].map(exchange => (
              <label key={exchange} className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.exchanges.includes(exchange)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSettings({ ...settings, exchanges: [...settings.exchanges, exchange] });
                    } else {
                      setSettings({ ...settings, exchanges: settings.exchanges.filter(ex => ex !== exchange) });
                    }
                  }}
                  disabled={isRunning}
                  className="mr-3"
                />
                <span className="capitalize">{exchange}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Advanced Options */}
        <div className="p-4 bg-gray-700 rounded-lg">
          <span className="text-sm text-gray-400 block mb-3">Advanced Options</span>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <label>
                <span className="text-xs text-gray-500">Batch Size</span>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={settings.batch_size}
                  onChange={(e) => setSettings({ ...settings, batch_size: Number(e.target.value) })}
                  disabled={isRunning}
                  className="w-full mt-1 px-3 py-2 bg-gray-800 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                />
              </label>
              
              <label className="flex items-center pt-5">
                <input
                  type="checkbox"
                  checked={settings.parallel}
                  onChange={(e) => setSettings({ ...settings, parallel: e.target.checked })}
                  disabled={isRunning}
                  className="mr-2"
                />
                <span>Parallel Processing</span>
              </label>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-3">
          {!isRunning ? (
            <button
              onClick={startBackfill}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Start Backfill
            </button>
          ) : (
            <button
              onClick={stopBackfill}
              className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              Stop Backfill
            </button>
          )}
        </div>
      </div>

      {/* Warning */}
      <div className="p-4 bg-yellow-900/30 border border-yellow-700 rounded-lg">
        <div className="flex items-start">
          <span className="text-yellow-500 mr-2">⚠️</span>
          <div className="text-sm text-yellow-400">
            <div className="font-medium mb-1">Important Notes:</div>
            <ul className="space-y-1 text-yellow-500">
              <li>• Backfilling large date ranges may take significant time</li>
              <li>• API rate limits may slow down the process</li>
              <li>• Database storage will increase with historical data</li>
              <li>• You can stop and resume backfill operations safely</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BackfillSettings;