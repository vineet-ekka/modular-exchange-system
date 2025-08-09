import React, { useState, useEffect } from 'react';
import Header from './components/Layout/Header';
import StatCard from './components/Cards/StatCard';
import AssetFundingGrid from './components/Grid/AssetFundingGrid';
import HistoricalFundingView from './components/Grid/HistoricalFundingView';
import { 
  fetchStatistics, 
  Statistics
} from './services/api';

function App() {
  const [stats, setStats] = useState<Statistics | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Fetch statistics only
  useEffect(() => {
    const loadStats = async () => {
      setLoading(true);
      try {
        const statsData = await fetchStatistics();
        setStats(statsData);
        setLastUpdate(new Date());
      } catch (error) {
        console.error('Error loading statistics:', error);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleAssetClick = (asset: string) => {
    setSelectedAsset(asset);
  };

  const handleCloseHistorical = () => {
    setSelectedAsset(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Header lastUpdate={lastUpdate} />
      
      <main className="p-6">
        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard
            title="Total Contracts"
            value={stats?.total_contracts || 0}
            icon="📊"
            color="blue"
          />
          <StatCard
            title="Average APR"
            value={`${stats?.avg_apr?.toFixed(2) || 0}%`}
            icon="📈"
            color="green"
          />
          <StatCard
            title="Highest APR"
            value={`${stats?.highest_apr?.toFixed(2) || 0}%`}
            subtitle={stats?.highest_symbol ? `${stats.highest_exchange} - ${stats.highest_symbol}` : undefined}
            icon="🚀"
            color="purple"
          />
          <StatCard
            title="Exchange"
            value="Binance"
            icon="🏛️"
            color="indigo"
          />
        </div>

        {/* Additional Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-800 rounded-xl p-4 shadow-xl">
            <div className="text-gray-400 text-sm">Unique Assets</div>
            <div className="text-2xl font-bold text-white mt-1">
              {stats?.unique_assets || 0}
            </div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 shadow-xl">
            <div className="text-gray-400 text-sm">Total Open Interest</div>
            <div className="text-2xl font-bold text-white mt-1">
              ${((stats?.total_open_interest || 0) / 1000000000).toFixed(2)}B
            </div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 shadow-xl">
            <div className="text-gray-400 text-sm">Lowest APR</div>
            <div className="text-2xl font-bold text-red-400 mt-1">
              {stats?.lowest_apr?.toFixed(2) || 0}%
            </div>
            {stats?.lowest_symbol && (
              <div className="text-xs text-gray-500 mt-1">
                {stats.lowest_exchange} - {stats.lowest_symbol}
              </div>
            )}
          </div>
        </div>

        {/* Asset Funding Grid - Main View */}
        <AssetFundingGrid onAssetClick={handleAssetClick} />

        {/* Historical View Modal */}
        {selectedAsset && (
          <HistoricalFundingView 
            asset={selectedAsset}
            onClose={handleCloseHistorical}
          />
        )}

        {/* Footer */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>Data updates every 30 seconds • Asset-based funding rates view</p>
          <p className="mt-1 text-xs">Click any asset to view historical charts</p>
        </div>
      </main>
    </div>
  );
}

export default App;