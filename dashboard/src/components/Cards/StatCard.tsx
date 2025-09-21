import React from 'react';
import clsx from 'clsx';
import ModernCard from '../Modern/ModernCard';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  loading?: boolean;
  onClick?: () => void;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  change,
  changeLabel,
  subtitle,
  icon,
  trend,
  loading = false,
  onClick,
}) => {
  // Determine trend from change if not explicitly provided
  const actualTrend = trend || (change !== undefined ? (change > 0 ? 'up' : change < 0 ? 'down' : 'neutral') : undefined);

  const trendColors = {
    up: 'text-success',
    down: 'text-danger',
    neutral: 'text-gray-500',
  };

  const trendIcons = {
    up: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
    down: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
      </svg>
    ),
    neutral: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
      </svg>
    ),
  };

  if (loading) {
    return (
      <ModernCard variant="elevated" padding="lg">
        <div className="space-y-3">
          <div className="skeleton h-4 w-24" />
          <div className="skeleton h-8 w-32" />
          <div className="skeleton h-3 w-16" />
        </div>
      </ModernCard>
    );
  }

  return (
    <ModernCard
      variant="elevated"
      padding="lg"
      hover={!!onClick}
      onClick={onClick}
      className="group"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-text-secondary">
              {title}
            </p>
            {icon && (
              <span className="text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                {icon}
              </span>
            )}
          </div>

          <p className="text-3xl font-bold mt-2 text-text-primary tracking-tight">
            {value || '—'}
          </p>

          {subtitle && (
            <p className="text-xs text-text-tertiary mt-1">
              {subtitle}
            </p>
          )}

          {(change !== undefined || changeLabel) && actualTrend && (
            <div className={clsx(
              'flex items-center gap-1 mt-3',
              trendColors[actualTrend]
            )}>
              {trendIcons[actualTrend]}
              <span className="text-sm font-medium">
                {change !== undefined && (
                  <>{change > 0 ? '+' : ''}{change}%</>
                )}
                {changeLabel && (
                  <span className="ml-1 text-xs">{changeLabel}</span>
                )}
              </span>
            </div>
          )}
        </div>

        {icon && !change && !changeLabel && (
          <div className="text-primary/10">
            <div className="text-4xl">
              {icon}
            </div>
          </div>
        )}
      </div>
    </ModernCard>
  );
};

export default StatCard;