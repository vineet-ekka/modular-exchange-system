import React, { useState, useEffect } from 'react';
import { Label } from '../ui/label';

interface APRRangeFilterProps {
  minApr: number | null;
  maxApr: number | null;
  onChange: (range: { minApr: number | null; maxApr: number | null }) => void;
}

export const APRRangeFilter: React.FC<APRRangeFilterProps> = ({
  minApr,
  maxApr,
  onChange
}) => {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (minApr !== null && maxApr !== null && minApr > maxApr) {
      setError('Min APR cannot exceed Max APR');
    } else {
      setError(null);
    }
  }, [minApr, maxApr]);

  const handleMinChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange({
      minApr: value === 'null' ? null : Number(value),
      maxApr
    });
  };

  const handleMaxChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange({
      minApr,
      maxApr: value === 'null' ? null : Number(value)
    });
  };

  return (
    <div className="mb-6 last:mb-0">
      <div className="text-muted-foreground text-xs font-semibold uppercase tracking-wider mb-3">
        APR Spread
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label className="text-muted-foreground text-sm font-medium">Min APR Spread</Label>
          <select
            className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground cursor-pointer appearance-none transition-colors hover:border-gray-300 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10 bg-no-repeat bg-[length:20px] bg-[right_8px_center] pr-10"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`
            }}
            value={minApr === null ? 'null' : minApr}
            onChange={handleMinChange}
            aria-label="Min APR"
          >
            <option value="null">No minimum</option>
            <option value="5">5%</option>
            <option value="10">10%</option>
            <option value="20">20%</option>
            <option value="30">30%</option>
            <option value="50">50%</option>
            <option value="75">75%</option>
            <option value="100">100%</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-muted-foreground text-sm font-medium">Max APR Spread</Label>
          <select
            className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground cursor-pointer appearance-none transition-colors hover:border-gray-300 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10 bg-no-repeat bg-[length:20px] bg-[right_8px_center] pr-10"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`
            }}
            value={maxApr === null ? 'null' : maxApr}
            onChange={handleMaxChange}
            aria-label="Max APR"
          >
            <option value="50">50%</option>
            <option value="100">100%</option>
            <option value="200">200%</option>
            <option value="500">500%</option>
            <option value="1000">1000%</option>
            <option value="null">No limit</option>
          </select>
        </div>
      </div>

      {error && (
        <p className="mt-2 text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  );
};

export default APRRangeFilter;
