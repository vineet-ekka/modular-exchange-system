import React from 'react';
import { Button } from '../ui/button';
import { cn } from '@/lib/utils';

const FUNDING_INTERVALS = [
  { hours: 1, label: '1 hour' },
  { hours: 4, label: '4 hours' },
  { hours: 8, label: '8 hours' },
  { hours: 24, label: '24 hours' },
];

interface IntervalSelectorProps {
  selectedIntervals: Set<number>;
  onChange: (intervals: Set<number>) => void;
}

export const IntervalSelector: React.FC<IntervalSelectorProps> = ({
  selectedIntervals,
  onChange
}) => {
  const toggleInterval = (hours: number) => {
    const newSet = new Set(selectedIntervals);
    if (newSet.has(hours)) {
      newSet.delete(hours);
    } else {
      newSet.add(hours);
    }
    onChange(newSet);
  };

  return (
    <div className="mb-6 last:mb-0">
      <div className="text-muted-foreground text-xs font-semibold uppercase tracking-wider mb-3">
        Funding Intervals
      </div>

      <div className="flex flex-wrap gap-2">
        {FUNDING_INTERVALS.map(({ hours, label }) => (
          <Button
            key={hours}
            variant={selectedIntervals.has(hours) ? "default" : "outline"}
            size="sm"
            onClick={() => toggleInterval(hours)}
            className={cn(
              "rounded-full px-3.5",
              !selectedIntervals.has(hours) && "text-muted-foreground hover:text-foreground"
            )}
          >
            {label}
          </Button>
        ))}
      </div>

      {selectedIntervals.size === 0 && (
        <p className="mt-2 text-xs text-muted-foreground">
          No intervals selected - showing all opportunities
        </p>
      )}
    </div>
  );
};

export default IntervalSelector;
