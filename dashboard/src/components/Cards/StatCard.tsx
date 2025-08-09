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
  const colorClasses = {
    blue: 'from-blue-600 to-blue-700',
    green: 'from-green-600 to-green-700',
    purple: 'from-purple-600 to-purple-700',
    indigo: 'from-indigo-600 to-indigo-700',
  };

  return (
    <div className={clsx(
      'bg-gradient-to-r rounded-xl p-6 text-white shadow-xl',
      colorClasses[color]
    )}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-white/80 text-sm font-medium">{title}</p>
          <p className="text-3xl font-bold mt-2">{value || '—'}</p>
          {subtitle && (
            <p className="text-white/60 text-xs mt-1">{subtitle}</p>
          )}
          {change !== undefined && (
            <p className={clsx(
              'text-sm mt-2',
              change > 0 ? 'text-green-300' : 'text-red-300'
            )}>
              {change > 0 ? '↑' : '↓'} {Math.abs(change)}%
            </p>
          )}
        </div>
        <div className="text-4xl opacity-50">{icon}</div>
      </div>
    </div>
  );
};

export default StatCard;