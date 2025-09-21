import React from 'react';
import clsx from 'clsx';

interface ModernInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
  variant?: 'default' | 'filled' | 'ghost';
}

const ModernInput: React.FC<ModernInputProps> = ({
  label,
  error,
  helperText,
  icon,
  iconPosition = 'left',
  fullWidth = false,
  variant = 'default',
  className,
  id,
  ...props
}) => {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

  const variantClasses = {
    default: 'border border-border bg-white focus:border-primary',
    filled: 'border border-transparent bg-gray-100 focus:bg-white focus:border-primary',
    ghost: 'border-b border-border bg-transparent rounded-none focus:border-primary',
  };

  return (
    <div className={clsx('space-y-1', { 'w-full': fullWidth })}>
      {label && (
        <label
          htmlFor={inputId}
          className="block text-sm font-medium text-text-secondary"
        >
          {label}
        </label>
      )}

      <div className="relative">
        {icon && iconPosition === 'left' && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-text-tertiary">
            {icon}
          </div>
        )}

        <input
          id={inputId}
          className={clsx(
            'w-full px-3 py-2 text-sm rounded-md transition-all duration-200',
            'placeholder:text-text-tertiary',
            'focus:outline-none focus:ring-2 focus:ring-primary/20',
            'disabled:cursor-not-allowed disabled:opacity-50',
            variantClasses[variant],
            {
              'pl-10': icon && iconPosition === 'left',
              'pr-10': icon && iconPosition === 'right',
              'border-danger focus:border-danger focus:ring-danger/20': error,
            },
            className
          )}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
          {...props}
        />

        {icon && iconPosition === 'right' && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-text-tertiary">
            {icon}
          </div>
        )}
      </div>

      {error && (
        <p id={`${inputId}-error`} className="text-xs text-danger">
          {error}
        </p>
      )}

      {helperText && !error && (
        <p id={`${inputId}-helper`} className="text-xs text-text-tertiary">
          {helperText}
        </p>
      )}
    </div>
  );
};

export default ModernInput;