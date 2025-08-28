import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ExchangeSettings from '../components/Settings/ExchangeSettings';
import DataFetchingSettings from '../components/Settings/DataFetchingSettings';
import BackfillSettings from '../components/Settings/BackfillSettings';
import AdvancedSettings from '../components/Settings/AdvancedSettings';

interface Settings {
  exchanges: {
    enabled: Record<string, boolean>;
    collection_mode: 'sequential' | 'parallel';
    collection_delay: number;
  };
  data_fetching: {
    enable_funding_rate: boolean;
    enable_open_interest: boolean;
    api_delay: number;
    display_limit: number;
    sort_column: string;
    sort_ascending: boolean;
  };
  historical: {
    enable_collection: boolean;
    fetch_interval: number;
    max_retries: number;
    base_backoff: number;
  };
  database: {
    host: string;
    port: string;
    database: string;
    user: string;
    table_name: string;
    historical_table: string;
  };
  output: {
    enable_csv: boolean;
    enable_database: boolean;
    enable_console: boolean;
    csv_filename: string;
  };
  debug: {
    debug_mode: boolean;
    show_sample_data: boolean;
  };
}

const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [originalSettings, setOriginalSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('exchanges');
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  // Load settings on mount
  useEffect(() => {
    fetchSettings();
  }, []);

  // Check for changes
  useEffect(() => {
    if (settings && originalSettings) {
      setHasChanges(JSON.stringify(settings) !== JSON.stringify(originalSettings));
    }
  }, [settings, originalSettings]);

  const fetchSettings = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/settings');
      const data = await response.json();
      if (data.status === 'success') {
        setSettings(data.settings);
        setOriginalSettings(JSON.parse(JSON.stringify(data.settings)));
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
      setMessage({ type: 'error', text: 'Failed to load settings' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!settings) return;
    
    setSaving(true);
    setMessage(null);
    
    try {
      // Validate settings first
      const validateResponse = await fetch('http://localhost:8000/api/settings/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      const validateData = await validateResponse.json();
      
      if (!validateData.valid) {
        setMessage({ 
          type: 'error', 
          text: `Validation errors: ${validateData.errors.join(', ')}` 
        });
        setSaving(false);
        return;
      }
      
      // Save settings
      const response = await fetch('http://localhost:8000/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      
      const data = await response.json();
      
      if (response.ok && data.status === 'success') {
        setMessage({ type: 'success', text: data.message });
        setOriginalSettings(JSON.parse(JSON.stringify(settings)));
        setHasChanges(false);
      } else {
        setMessage({ type: 'error', text: data.detail || 'Failed to save settings' });
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      setMessage({ type: 'error', text: 'Failed to save settings' });
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (originalSettings) {
      setSettings(JSON.parse(JSON.stringify(originalSettings)));
      setHasChanges(false);
      setMessage(null);
    }
  };

  const handleExport = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/settings/export');
      const data = await response.json();
      
      // Download as JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `settings_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
      setMessage({ type: 'success', text: 'Settings exported successfully' });
    } catch (error) {
      console.error('Error exporting settings:', error);
      setMessage({ type: 'error', text: 'Failed to export settings' });
    }
  };

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    try {
      const text = await file.text();
      const importData = JSON.parse(text);
      
      const response = await fetch('http://localhost:8000/api/settings/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(importData)
      });
      
      const data = await response.json();
      
      if (response.ok && data.status === 'success') {
        setMessage({ type: 'success', text: data.message });
        await fetchSettings(); // Reload settings
      } else {
        setMessage({ type: 'error', text: data.detail || 'Failed to import settings' });
      }
    } catch (error) {
      console.error('Error importing settings:', error);
      setMessage({ type: 'error', text: 'Failed to import settings' });
    }
    
    // Reset file input
    event.target.value = '';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="text-xl">Loading settings...</div>
          </div>
        </div>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="text-xl text-red-500">Failed to load settings</div>
          </div>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'exchanges', label: 'Exchanges', icon: '🔄' },
    { id: 'fetching', label: 'Data Fetching', icon: '📊' },
    { id: 'backfill', label: 'Backfill', icon: '📥' },
    { id: 'advanced', label: 'Advanced', icon: '⚙️' }
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold mb-2">System Settings</h1>
              <p className="text-gray-400">Configure exchange connections, data collection, and system behavior</p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            >
              ← Back to Dashboard
            </button>
          </div>
        </div>

        {/* Message */}
        {message && (
          <div className={`mb-6 p-4 rounded-lg ${
            message.type === 'success' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
          }`}>
            {message.text}
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex space-x-1 mb-6 bg-gray-800 p-1 rounded-lg">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 px-4 py-2 rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          {activeTab === 'exchanges' && (
            <ExchangeSettings 
              settings={settings.exchanges}
              onChange={(exchanges) => setSettings({ ...settings, exchanges })}
            />
          )}
          {activeTab === 'fetching' && (
            <DataFetchingSettings
              settings={settings.data_fetching}
              historicalSettings={settings.historical}
              outputSettings={settings.output}
              onChange={(data_fetching) => setSettings({ ...settings, data_fetching })}
              onHistoricalChange={(historical) => setSettings({ ...settings, historical })}
              onOutputChange={(output) => setSettings({ ...settings, output })}
            />
          )}
          {activeTab === 'backfill' && (
            <BackfillSettings />
          )}
          {activeTab === 'advanced' && (
            <AdvancedSettings
              settings={settings.debug}
              databaseSettings={settings.database}
              onChange={(debug) => setSettings({ ...settings, debug })}
              onDatabaseChange={(database) => setSettings({ ...settings, database })}
            />
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between">
          <div className="flex space-x-2">
            <button
              onClick={handleExport}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              📤 Export Settings
            </button>
            <label className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors cursor-pointer">
              📥 Import Settings
              <input
                type="file"
                accept=".json"
                onChange={handleImport}
                className="hidden"
              />
            </label>
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={handleCancel}
              disabled={!hasChanges || saving}
              className={`px-6 py-2 rounded-lg transition-colors ${
                hasChanges && !saving
                  ? 'bg-gray-700 hover:bg-gray-600 text-white'
                  : 'bg-gray-800 text-gray-500 cursor-not-allowed'
              }`}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!hasChanges || saving}
              className={`px-6 py-2 rounded-lg transition-colors ${
                hasChanges && !saving
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-gray-800 text-gray-500 cursor-not-allowed'
              }`}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        {/* Changes indicator */}
        {hasChanges && (
          <div className="mt-4 text-center text-yellow-500 text-sm">
            ⚠️ You have unsaved changes
          </div>
        )}
      </div>
    </div>
  );
};

export default SettingsPage;