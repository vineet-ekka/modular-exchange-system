import React from 'react';
import clsx from 'clsx';

interface Option {
  value: string | number;
  label: string;
  disabled?: boolean;
}

interface ModernSelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'value' | 'onChange'> {
  label?: string;
  options: Option[];
  value?: string | number;
  onChange?: (value: string | number) => void;
  error?: string;
  helperText?: string;
  fullWidth?: boolean;
  variant?: 'default' | 'filled' | 'ghost';
  placeholder?: string;
}

const ModernSelect: React.FC<ModernSelectProps> = ({
  label,
  options,
  value,
  onChange,
  error,
  helperText,
  fullWidth = false,
  variant = 'default',
  placeholder = 'Select an option',
  className,
  id,
  disabled,
  ...props
}) => {
  const selectId = id || `select-${Math.random().toString(36).substr(2, 9)}`;

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange?.(e.target.value);
  };

  const variantClasses = {
    default: 'border border-border bg-white focus:border-primary',
    filled: 'border border-transparent bg-gray-100 focus:bg-white focus:border-primary',
    ghost: 'border-b border-border bg-transparent rounded-none focus:border-primary',
  };

  return (
    <div className={clsx('space-y-1', { 'w-full': fullWidth })}>
      {label && (
        <label
          htmlFor={selectId}
          className="block text-sm font-medium text-text-secondary"
        >
          {label}
        </label>
      )}

      <div className="relative">
        <select
          id={selectId}
          value={value}
          onChange={handleChange}
          disabled={disabled}
          className={clsx(
            'w-full px-3 py-2 pr-8 text-sm rounded-md appearance-none cursor-pointer transition-all duration-200',
            'focus:outline-none focus:ring-2 focus:ring-primary/20',
            'disabled:cursor-not-allowed disabled:opacity-50',
            variantClasses[variant],
            {
              'text-text-tertiary': !value,
              'border-danger focus:border-danger focus:ring-danger/20': error,
            },
            className
          )}
          aria-invalid={!!error}
          aria-describedby={error ? `${selectId}-error` : helperText ? `${selectId}-helper` : undefined}
          {...props}
        >
          <option value="" disabled>
            {placeholder}
          </option>
          {options.map((option) => (
            <option
              key={option.value}
              value={option.value}
              disabled={option.disabled}
            >
              {option.label}
            </option>
          ))}
        </select>

        <div className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
          <svg
            className="h-5 w-5 text-text-tertiary"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </div>
      </div>

      {error && (
        <p id={`${selectId}-error`} className="text-xs text-danger">
          {error}
        </p>
      )}

      {helperText && !error && (
        <p id={`${selectId}-helper`} className="text-xs text-text-tertiary">
          {helperText}
        </p>
      )}
    </div>
  );
};

export default ModernSelect;