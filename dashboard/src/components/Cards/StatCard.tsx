import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { cn } from '../../lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  loading?: boolean;
  onClick?: () => void;
  className?: string;
  valueClassName?: string;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  loading = false,
  onClick,
  className,
  valueClassName,
}) => {
  if (loading) {
    return (
      <Card className={cn("shadow-md", className)}>
        <CardHeader className="p-4 pb-2">
          <Skeleton className="h-4 w-24" />
        </CardHeader>
        <CardContent className="px-4 pb-4 pt-0">
          <Skeleton className="h-8 w-20" />
          {subtitle !== undefined && <Skeleton className="h-3 w-32 mt-2" />}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      onClick={onClick}
      className={cn(
        "shadow-md hover:shadow-lg transition-all duration-200",
        onClick && "cursor-pointer hover:-translate-y-0.5",
        className
      )}
    >
      <CardHeader className="p-4 pb-2 text-center">
        <CardTitle className="text-sm font-medium text-text-secondary">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 pt-0 text-center">
        <p className={cn(
          "text-2xl font-bold text-text-primary tracking-tight",
          valueClassName
        )}>
          {value}
        </p>
        {subtitle && (
          <p className="text-xs text-text-tertiary mt-1">
            {subtitle}
          </p>
        )}
      </CardContent>
    </Card>
  );
};

export default StatCard;
