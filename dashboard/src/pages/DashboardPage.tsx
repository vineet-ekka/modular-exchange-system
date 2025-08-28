import React, { useState, useEffect } from 'react';
import Header from '../components/Layout/Header';
import StatCard from '../components/Cards/StatCard';
import AssetFundingGrid from '../components/Grid/AssetFundingGrid';
import { 
  fetchStatistics, 
  Statistics
} from '../services/api';

function DashboardPage() {
  const [stats, setStats] = useState<Statistics | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Fetch statistics only
  useEffect(() => {
    const loadStats = async () => {
      try {
        const statsData = await fetchStatistics();
        setStats(statsData);
        setLastUpdate(new Date());
      } catch (error) {
        console.error('Error loading statistics:', error);
      }
    };

    loadStats();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-light-bg">
      <Header lastUpdate={lastUpdate} />
      
      <main className="p-6">
        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard
            title="Total Contracts"
            value={stats?.total_contracts || 0}
            icon=""
            color="blue"
          />
          <StatCard
            title="Average APR"
            value={`${stats?.avg_apr?.toFixed(2) || 0}%`}
            icon=""
            color="green"
          />
          <StatCard
            title="Highest APR"
            value={`${stats?.highest_apr?.toFixed(2) || 0}%`}
            subtitle={stats?.highest_symbol ? `${stats.highest_exchange} - ${stats.highest_symbol}` : undefined}
            icon=""
            color="purple"
          />
          <StatCard
            title="Exchange"
            value="Binance"
            icon=""
            color="indigo"
          />
        </div>

        {/* Additional Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          <div className="bg-light-card rounded-xl p-4 shadow-lg border border-light-border">
            <div className="text-text-secondary text-sm">Unique Assets</div>
            <div className="text-2xl font-bold text-text-primary mt-1">
              {stats?.unique_assets || 0}
            </div>
          </div>
          <div className="bg-light-card rounded-xl p-4 shadow-lg border border-light-border">
            <div className="text-text-secondary text-sm">Total Open Interest</div>
            <div className="text-2xl font-bold text-text-primary mt-1">
              ${((stats?.total_open_interest || 0) / 1000000000).toFixed(2)}B
            </div>
          </div>
          <div className="bg-light-card rounded-xl p-4 shadow-lg border border-light-border">
            <div className="text-text-secondary text-sm">Lowest APR</div>
            <div className="text-2xl font-bold text-funding-negative mt-1">
              {stats?.lowest_apr?.toFixed(2) || 0}%
            </div>
            {stats?.lowest_symbol && (
              <div className="text-xs text-text-muted mt-1">
                {stats.lowest_exchange} - {stats.lowest_symbol}
              </div>
            )}
          </div>
        </div>

        {/* Asset Funding Grid - Main View */}
        <AssetFundingGrid />

        {/* Footer */}
        <div className="mt-8 text-center text-text-secondary text-sm">
          <p>Data updates every 30 seconds • Asset-based funding rates view</p>
          <p className="mt-1 text-xs text-text-muted">Click any asset to view historical charts</p>
        </div>
      </main>
    </div>
  );
}

export default DashboardPage;