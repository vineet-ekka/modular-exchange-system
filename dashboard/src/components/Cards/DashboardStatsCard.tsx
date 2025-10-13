import React from 'react';
import ModernCard from '../Modern/ModernCard';

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
  if (loading) {
    return (
      <ModernCard variant="elevated" padding="lg">
        <div className="space-y-4">
          <div className="skeleton h-5 w-40" />
          <div className="grid grid-cols-3 gap-6">
            <div className="skeleton h-16" />
            <div className="skeleton h-16" />
            <div className="skeleton h-16" />
          </div>
          <div className="skeleton h-px w-full" />
          <div className="grid grid-cols-2 gap-6">
            <div className="skeleton h-16" />
            <div className="skeleton h-16" />
          </div>
        </div>
      </ModernCard>
    );
  }

  const systemMetrics = [
    {
      label: 'Total Contracts',
      value: totalContracts,
    },
    {
      label: 'Unique Assets',
      value: uniqueAssets,
    },
    {
      label: 'Active Exchanges',
      value: activeExchanges,
    },
  ];

  return (
    <ModernCard variant="elevated" padding="lg">
      <div className="space-y-6">
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
          Dashboard Statistics
        </h3>

        <div className="grid grid-cols-3 gap-6">
          {systemMetrics.map((metric) => (
            <div key={metric.label} className="flex flex-col items-center text-center">
              <p className="text-3xl font-bold text-text-primary mb-1">
                {metric.value.toLocaleString()}
              </p>
              <p className="text-xs font-medium text-text-tertiary">
                {metric.label}
              </p>
            </div>
          ))}
        </div>

        <div className="border-t border-border" />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="flex flex-col items-center text-center">
            <p className="text-xs font-medium text-success mb-2">
              Highest
            </p>
            <p className="text-2xl font-bold text-text-primary tracking-tight">
              {highestAPR.toFixed(2)}%
            </p>
            {highestSymbol && highestExchange && (
              <p className="text-xs text-text-tertiary mt-1">
                {highestExchange} - {highestSymbol}
              </p>
            )}
          </div>

          <div className="flex flex-col items-center text-center border-t md:border-t-0 md:border-l border-border pt-6 md:pt-0">
            <p className="text-xs font-medium text-danger mb-2">
              Lowest
            </p>
            <p className="text-2xl font-bold text-text-primary tracking-tight">
              {lowestAPR.toFixed(2)}%
            </p>
            {lowestSymbol && lowestExchange && (
              <p className="text-xs text-text-tertiary mt-1">
                {lowestExchange} - {lowestSymbol}
              </p>
            )}
          </div>
        </div>
      </div>
    </ModernCard>
  );
};

export default DashboardStatsCard;
