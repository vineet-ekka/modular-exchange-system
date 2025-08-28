import React from 'react';
import clsx from 'clsx';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  subtitle?: string;
  icon: string;
  color?: 'blue' | 'green' | 'purple' | 'indigo';
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, 
  value, 
  change, 
  subtitle, 
  icon, 
  color = 'blue' 
}) => {
  // Using simpler card style matching the reference image
  return (
    <div className="bg-white rounded-xl p-6 shadow-lg border border-light-border">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-text-secondary text-sm font-medium">{title}</p>
          <p className="text-3xl font-bold mt-2 text-text-primary">{value || '—'}</p>
          {subtitle && (
            <p className="text-text-muted text-xs mt-1">{subtitle}</p>
          )}
          {change !== undefined && (
            <p className={clsx(
              'text-sm mt-2',
              change > 0 ? 'text-funding-positive' : 'text-funding-negative'
            )}>
              {change > 0 ? '↑' : '↓'} {Math.abs(change)}%
            </p>
          )}
        </div>
        {icon && <div className="text-4xl opacity-30 text-text-muted">{icon}</div>}
      </div>
    </div>
  );
};

export default StatCard;