import React from 'react';
import ModernCard from '../Modern/ModernCard';

interface APRExtremeCardProps {
  highestAPR: number;
  highestExchange?: string;
  highestSymbol?: string;
  lowestAPR: number;
  lowestExchange?: string;
  lowestSymbol?: string;
  loading?: boolean;
}

const APRExtremeCard: React.FC<APRExtremeCardProps> = ({
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
        <div className="space-y-3">
          <div className="skeleton h-4 w-32" />
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div className="skeleton h-16" />
            <div className="skeleton h-16" />
          </div>
        </div>
      </ModernCard>
    );
  }

  return (
    <ModernCard variant="elevated" padding="lg">
      <p className="text-sm font-medium text-text-secondary mb-4">
        APR Extremes
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col">
          <div className="flex items-center gap-2 text-success mb-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            <span className="text-xs font-medium">Highest</span>
          </div>
          <p className="text-2xl font-bold text-text-primary tracking-tight">
            {highestAPR.toFixed(2)}%
          </p>
          {highestSymbol && highestExchange && (
            <p className="text-xs text-text-tertiary mt-1">
              {highestExchange} - {highestSymbol}
            </p>
          )}
        </div>

        <div className="flex flex-col border-t md:border-t-0 md:border-l border-border pt-4 md:pt-0 md:pl-4">
          <div className="flex items-center gap-2 text-danger mb-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
            </svg>
            <span className="text-xs font-medium">Lowest</span>
          </div>
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
    </ModernCard>
  );
};

export default APRExtremeCard;
