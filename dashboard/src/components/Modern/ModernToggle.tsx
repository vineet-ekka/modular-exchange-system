import React from 'react';
import clsx from 'clsx';

interface ModernToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  color?: 'primary' | 'success' | 'danger';
  className?: string;
}

const ModernToggle: React.FC<ModernToggleProps> = ({
  checked,
  onChange,
  disabled = false,
  label,
  size = 'md',
  color = 'primary',
  className,
}) => {
  const handleToggle = () => {
    if (!disabled) {
      onChange(!checked);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      handleToggle();
    }
  };

  const sizeClasses = {
    sm: {
      track: 'w-8 h-4',
      thumb: 'w-3 h-3',
      translate: 'translate-x-4',
    },
    md: {
      track: 'w-11 h-6',
      thumb: 'w-5 h-5',
      translate: 'translate-x-5',
    },
    lg: {
      track: 'w-14 h-7',
      thumb: 'w-6 h-6',
      translate: 'translate-x-7',
    },
  };

  const colorClasses = {
    primary: 'bg-primary',
    success: 'bg-success',
    danger: 'bg-danger',
  };

  return (
    <label
      className={clsx(
        'inline-flex items-center',
        {
          'cursor-pointer': !disabled,
          'cursor-not-allowed opacity-50': disabled,
        },
        className
      )}
    >
      <div className="relative">
        <input
          type="checkbox"
          className="sr-only"
          checked={checked}
          onChange={() => onChange(checked)}
          disabled={disabled}
          onKeyDown={handleKeyDown}
        />

        <div
          className={clsx(
            'block rounded-full transition-colors duration-200',
            sizeClasses[size].track,
            {
              [colorClasses[color]]: checked,
              'bg-gray-300': !checked,
            }
          )}
          onClick={handleToggle}
        >
          <div
            className={clsx(
              'absolute left-0.5 top-0.5 bg-white rounded-full shadow-sm transition-transform duration-200',
              sizeClasses[size].thumb,
              {
                [sizeClasses[size].translate]: checked,
              }
            )}
          />
        </div>
      </div>

      {label && (
        <span className={clsx(
          'ml-3 text-sm font-medium text-text-primary',
          { 'select-none': !disabled }
        )}>
          {label}
        </span>
      )}
    </label>
  );
};

export default ModernToggle;