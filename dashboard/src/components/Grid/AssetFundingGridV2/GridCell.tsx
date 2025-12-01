import React, { memo } from 'react';
import { cn } from '../../../lib/utils';
import { getRateBgColorCached, getRateColor, formatValue } from './utils';
import { ViewMode } from './types';

interface GridCellProps {
  value: number | null;
  viewMode: ViewMode;
  shouldHighlight: boolean;
}

const GridCellComponent: React.FC<GridCellProps> = ({
  value,
  viewMode,
  shouldHighlight,
}) => {
  const isMissing = value === null || value === undefined;

  return (
    <div
      className={cn(
        'relative',
        getRateBgColorCached(value),
        shouldHighlight && 'bg-orange-50 border border-orange-200'
      )}
    >
      <span className={getRateColor(value)}>
        {formatValue(value, viewMode)}
      </span>
      {shouldHighlight && (
        <div
          className="absolute top-1 right-1 w-1.5 h-1.5 bg-orange-400 rounded-full"
          title="No data available"
        ></div>
      )}
    </div>
  );
};

export const GridCell = memo(GridCellComponent, (prevProps, nextProps) => {
  return (
    prevProps.value === nextProps.value &&
    prevProps.viewMode === nextProps.viewMode &&
    prevProps.shouldHighlight === nextProps.shouldHighlight
  );
});

GridCell.displayName = 'GridCell';
