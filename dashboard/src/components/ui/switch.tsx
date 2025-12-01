import * as React from "react"
import { cn } from "@/lib/utils"

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
  className?: string;
}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ checked, onChange, disabled, label, className }, ref) => {
    return (
      <label className={cn(
        'inline-flex items-center',
        disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
        className
      )}>
        <div className="relative">
          <input
            ref={ref}
            type="checkbox"
            className="sr-only"
            checked={checked}
            onChange={(e) => onChange(e.target.checked)}
            disabled={disabled}
          />
          <div
            className={cn(
              'block w-11 h-6 rounded-full transition-colors duration-200',
              checked ? 'bg-primary' : 'bg-gray-300'
            )}
          >
            <div
              className={cn(
                'absolute left-0.5 top-0.5 w-5 h-5 bg-white rounded-full shadow-sm transition-transform duration-200',
                checked && 'translate-x-5'
              )}
            />
          </div>
        </div>
        {label && (
          <span className="ml-3 text-sm font-medium text-foreground select-none">
            {label}
          </span>
        )}
      </label>
    );
  }
);

Switch.displayName = "Switch";

export { Switch };
