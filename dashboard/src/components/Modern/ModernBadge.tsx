import React from 'react';
import clsx from 'clsx';

interface ModernBadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'danger' | 'warning' | 'info' | 'neutral';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  rounded?: boolean;
  className?: string;
  onClick?: () => void;
}

const ModernBadge: React.FC<ModernBadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  dot = false,
  rounded = true,
  className,
  onClick,
}) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-0.5 text-xs',
    lg: 'px-3 py-1 text-sm',
  };

  const variantClasses = {
    default: 'bg-primary/10 text-primary-700 border-primary/20',
    success: 'bg-success/10 text-success-700 border-success/20',
    danger: 'bg-danger/10 text-danger-700 border-danger/20',
    warning: 'bg-warning/10 text-warning-700 border-warning/20',
    info: 'bg-info/10 text-info-dark border-info/20',
    neutral: 'bg-gray-100 text-gray-700 border-gray-200',
  };

  const dotColors = {
    default: 'bg-primary',
    success: 'bg-success',
    danger: 'bg-danger',
    warning: 'bg-warning',
    info: 'bg-info',
    neutral: 'bg-gray-500',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium border transition-all duration-200',
        sizeClasses[size],
        variantClasses[variant],
        {
          'rounded-full': rounded,
          'rounded': !rounded,
          'cursor-pointer hover:opacity-80': onClick,
        },
        className
      )}
      onClick={onClick}
    >
      {dot && (
        <span
          className={clsx(
            'inline-block rounded-full mr-1.5',
            dotColors[variant],
            {
              'w-1.5 h-1.5': size === 'sm',
              'w-2 h-2': size === 'md',
              'w-2.5 h-2.5': size === 'lg',
            }
          )}
        />
      )}
      {children}
    </span>
  );
};

export default ModernBadge;