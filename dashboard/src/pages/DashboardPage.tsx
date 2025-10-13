import React, { useState, useEffect } from 'react';
import Header from '../components/Layout/Header';
import DashboardStatsCard from '../components/Cards/DashboardStatsCard';
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
    <div className="min-h-screen bg-background">
      <Header lastUpdate={lastUpdate} />

      <main className="py-6">
        <div className="container mx-auto px-4">
          <div className="mb-6">
            <DashboardStatsCard
              totalContracts={stats?.total_contracts || 0}
              uniqueAssets={stats?.unique_assets || 0}
              activeExchanges={stats?.active_exchanges || 0}
              highestAPR={stats?.highest_apr || 0}
              highestExchange={stats?.highest_exchange}
              highestSymbol={stats?.highest_symbol}
              lowestAPR={stats?.lowest_apr || 0}
              lowestExchange={stats?.lowest_exchange}
              lowestSymbol={stats?.lowest_symbol}
            />
          </div>
        </div>

        {/* Asset Funding Grid - Main View - Full Width */}
        <div className="w-full px-2">
          <AssetFundingGrid />
        </div>

        {/* Footer */}
        <div className="container mx-auto px-4 mt-8 text-center text-text-secondary text-sm">
          <p>Data updates every 30 seconds • Asset-based funding rates view</p>
          <p className="mt-1 text-xs text-text-muted">Click any asset to view historical charts</p>
        </div>
      </main>
    </div>
  );
}

export default DashboardPage;