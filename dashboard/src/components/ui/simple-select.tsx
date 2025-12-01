import * as React from "react"
import { cn } from "@/lib/utils"

interface Option {
  value: string | number;
  label: string;
  disabled?: boolean;
}

interface SimpleSelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'value' | 'onChange'> {
  label?: string;
  options: Option[];
  value?: string | number;
  onChange?: (value: string | number) => void;
  error?: string;
  helperText?: string;
  fullWidth?: boolean;
}

const SimpleSelect = React.forwardRef<HTMLSelectElement, SimpleSelectProps>(
  ({ label, options, value, onChange, error, helperText, fullWidth, className, id, ...props }, ref) => {
    const generatedId = React.useId();
    const selectId = id || generatedId;

    return (
      <div className={cn('space-y-1', fullWidth && 'w-full')}>
        {label && (
          <label htmlFor={selectId} className="block text-sm font-medium text-muted-foreground">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          className={cn(
            'w-full px-3 py-2 pr-8 text-sm rounded-md border border-input bg-background',
            'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
            'disabled:cursor-not-allowed disabled:opacity-50',
            error && 'border-destructive focus:ring-destructive',
            className
          )}
          aria-invalid={!!error}
          {...props}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
        {error && <p className="text-xs text-destructive">{error}</p>}
        {helperText && !error && <p className="text-xs text-muted-foreground">{helperText}</p>}
      </div>
    );
  }
);

SimpleSelect.displayName = "SimpleSelect";

export { SimpleSelect };
