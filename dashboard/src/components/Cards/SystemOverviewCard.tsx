import React from 'react';
import { Card } from '../ui/card';

interface SystemOverviewCardProps {
  totalContracts: number;
  uniqueAssets: number;
  activeExchanges: number;
  loading?: boolean;
}

const SystemOverviewCard: React.FC<SystemOverviewCardProps> = ({
  totalContracts,
  uniqueAssets,
  activeExchanges,
  loading = false,
}) => {
  if (loading) {
    return (
      <Card className="shadow-md hover:shadow-lg transition-shadow duration-200 p-6">
        <div className="space-y-4">
          <div className="skeleton h-5 w-32" />
          <div className="grid grid-cols-3 gap-6">
            <div className="skeleton h-12 w-full" />
            <div className="skeleton h-12 w-full" />
            <div className="skeleton h-12 w-full" />
          </div>
        </div>
      </Card>
    );
  }

  const metrics = [
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
    <Card className="shadow-md hover:shadow-lg transition-shadow duration-200 p-6">
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
          System Overview
        </h3>

        <div className="grid grid-cols-3 gap-6">
          {metrics.map((metric, index) => (
            <div key={metric.label} className="flex flex-col items-center text-center">
              <p className="text-2xl font-bold text-text-primary mb-1">
                {metric.value.toLocaleString()}
              </p>

              <p className="text-xs font-medium text-text-tertiary">
                {metric.label}
              </p>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
};

export default SystemOverviewCard;
