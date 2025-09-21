import React from 'react';
import clsx from 'clsx';

interface ModernCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'flat' | 'outlined' | 'elevated';
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
  onClick?: () => void;
  hover?: boolean;
  as?: React.ElementType;
}

const ModernCard: React.FC<ModernCardProps> = ({
  children,
  className,
  variant = 'default',
  padding = 'md',
  onClick,
  hover = false,
  as: Component = 'div',
}) => {
  const paddingClasses = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
    xl: 'p-8',
  };

  const variantClasses = {
    default: 'bg-white border border-border shadow-sm',
    flat: 'bg-white border border-border',
    outlined: 'bg-transparent border-2 border-border',
    elevated: 'bg-white shadow-md hover:shadow-lg transition-shadow duration-200',
  };

  return (
    <Component
      className={clsx(
        'rounded-lg transition-all duration-200',
        paddingClasses[padding],
        variantClasses[variant],
        {
          'cursor-pointer': onClick,
          'hover:shadow-md hover:-translate-y-0.5': hover && variant !== 'elevated',
          'hover:border-primary/50': hover && variant === 'outlined',
        },
        className
      )}
      onClick={onClick}
    >
      {children}
    </Component>
  );
};

export default ModernCard;