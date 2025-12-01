import React from 'react';
import StatCard from './StatCard';

interface DashboardStatsCardProps {
  totalContracts: number;
  uniqueAssets: number;
  activeExchanges: number;
  highestAPR: number;
  highestExchange?: string;
  highestSymbol?: string;
  lowestAPR: number;
  lowestExchange?: string;
  lowestSymbol?: string;
  loading?: boolean;
}

const DashboardStatsCard: React.FC<DashboardStatsCardProps> = ({
  totalContracts,
  uniqueAssets,
  activeExchanges,
  highestAPR,
  highestExchange,
  highestSymbol,
  lowestAPR,
  lowestExchange,
  lowestSymbol,
  loading = false,
}) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      <StatCard
        title="Total Contracts"
        value={totalContracts.toLocaleString()}
        loading={loading}
      />
      <StatCard
        title="Unique Assets"
        value={uniqueAssets.toLocaleString()}
        loading={loading}
      />
      <StatCard
        title="Active Exchanges"
        value={activeExchanges.toLocaleString()}
        loading={loading}
      />
      <StatCard
        title="Highest APR"
        value={`${highestAPR.toFixed(2)}%`}
        subtitle={highestExchange && highestSymbol ? `${highestExchange} - ${highestSymbol}` : undefined}
        loading={loading}
        valueClassName="text-success"
      />
      <StatCard
        title="Lowest APR"
        value={`${lowestAPR.toFixed(2)}%`}
        subtitle={lowestExchange && lowestSymbol ? `${lowestExchange} - ${lowestSymbol}` : undefined}
        loading={loading}
        valueClassName="text-danger"
      />
    </div>
  );
};

export default DashboardStatsCard;
