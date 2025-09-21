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
    <div className="min-h-screen bg-background">
      <Header lastUpdate={lastUpdate} />

      <main className="py-6">
        {/* Main Statistics Cards */}
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
          <StatCard
            title="Total Contracts"
            value={stats?.total_contracts || 0}
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            }
          />
          <StatCard
            title="Average APR"
            value={`${stats?.avg_apr?.toFixed(2) || 0}%`}
            trend="neutral"
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
              </svg>
            }
          />
          <StatCard
            title="Highest APR"
            value={`${stats?.highest_apr?.toFixed(2) || 0}%`}
            subtitle={stats?.highest_symbol ? `${stats.highest_exchange} - ${stats.highest_symbol}` : undefined}
            trend="up"
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            }
          />
          <StatCard
            title="Active Exchanges"
            value="4"
            subtitle="Binance, KuCoin, Backpack, Hyperliquid"
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
            }
          />
        </div>

          {/* Secondary Statistics Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <StatCard
            title="Unique Assets"
            value={stats?.unique_assets || 0}
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            }
          />
          <StatCard
            title="Total Open Interest"
            value={`$${((stats?.total_open_interest || 0) / 1000000000).toFixed(2)}B`}
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
          />
          <StatCard
            title="Lowest APR"
            value={`${stats?.lowest_apr?.toFixed(2) || 0}%`}
            subtitle={stats?.lowest_symbol ? `${stats.lowest_exchange} - ${stats.lowest_symbol}` : undefined}
            trend="down"
            icon={
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
              </svg>
            }
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