import React from 'react';
import { Label } from '../ui/label';

interface LiquidityFilterProps {
  minOIEither: number | null;
  minOICombined: number | null;
  onChange: (liquidity: { minOIEither: number | null; minOICombined: number | null }) => void;
}

export const LiquidityFilter: React.FC<LiquidityFilterProps> = ({
  minOIEither,
  minOICombined,
  onChange
}) => {
  const handleEitherChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange({
      minOIEither: value === 'null' ? null : Number(value),
      minOICombined
    });
  };

  const handleCombinedChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange({
      minOIEither,
      minOICombined: value === 'null' ? null : Number(value)
    });
  };

  return (
    <div className="mb-6 last:mb-0">
      <div className="text-muted-foreground text-xs font-semibold uppercase tracking-wider mb-3">
        Liquidity Requirements
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label className="text-muted-foreground text-sm font-medium">Min OI (Either)</Label>
          <select
            className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground cursor-pointer appearance-none transition-colors hover:border-gray-300 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10 bg-no-repeat bg-[length:20px] bg-[right_8px_center] pr-10"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`
            }}
            value={minOIEither === null ? 'null' : minOIEither}
            onChange={handleEitherChange}
          >
            <option value="null">No minimum</option>
            <option value="10000">$10K</option>
            <option value="100000">$100K</option>
            <option value="1000000">$1M</option>
            <option value="10000000">$10M</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-muted-foreground text-sm font-medium">Min Combined OI</Label>
          <select
            className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground cursor-pointer appearance-none transition-colors hover:border-gray-300 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10 bg-no-repeat bg-[length:20px] bg-[right_8px_center] pr-10"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`
            }}
            value={minOICombined === null ? 'null' : minOICombined}
            onChange={handleCombinedChange}
          >
            <option value="null">No minimum</option>
            <option value="100000">$100K</option>
            <option value="500000">$500K</option>
            <option value="1000000">$1M</option>
            <option value="10000000">$10M</option>
          </select>
        </div>
      </div>

      <p className="mt-2 text-xs text-muted-foreground">
        Filter by minimum open interest for trade execution feasibility
      </p>
    </div>
  );
};

export default LiquidityFilter;
