import React, { useMemo } from 'react';
import Header from '../components/Layout/Header';
import DashboardStatsCard from '../components/Cards/DashboardStatsCard';
import AssetFundingGrid from '../components/Grid/AssetFundingGridV2';
import { useDashboardStats } from '../hooks/useDataQueries';

function DashboardPage() {
  const { data: stats, dataUpdatedAt } = useDashboardStats();

  const lastUpdate = useMemo(() => {
    return dataUpdatedAt ? new Date(dataUpdatedAt) : new Date();
  }, [dataUpdatedAt]);

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
          <p>Data updates every 30 seconds - Asset-based funding rates view</p>
          <p className="mt-1 text-xs text-text-muted">Click any asset to view historical charts</p>
        </div>
      </main>
    </div>
  );
}

export default DashboardPage;