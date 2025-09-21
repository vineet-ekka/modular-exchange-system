import React from 'react';
import clsx from 'clsx';

interface NeumorphicCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'flat' | 'convex' | 'concave';
  size?: 'sm' | 'md' | 'lg';
  hover?: boolean;
  onClick?: () => void;
}

const NeumorphicCard: React.FC<NeumorphicCardProps> = ({
  children,
  className,
  variant = 'flat',
  size = 'md',
  hover = false,
  onClick
}) => {
  const sizeClasses = {
    sm: 'p-3 rounded-lg',
    md: 'p-5 rounded-xl',
    lg: 'p-6 rounded-2xl'
  };

  const variantClasses = {
    flat: 'bg-neumorphic-bg shadow-neumorphic',
    convex: 'bg-gradient-to-br from-neumorphic-bg-light to-neumorphic-bg-dark shadow-neumorphic',
    concave: 'bg-gradient-to-br from-neumorphic-bg-dark to-neumorphic-bg-light shadow-neumorphic-inset'
  };

  return (
    <div
      className={clsx(
        'transition-all duration-200',
        sizeClasses[size],
        variantClasses[variant],
        hover && 'hover:shadow-neumorphic-hover cursor-pointer',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
    >
      {children}
    </div>
  );
};

export default NeumorphicCard;