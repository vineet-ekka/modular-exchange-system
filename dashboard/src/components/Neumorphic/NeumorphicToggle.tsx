import React from 'react';
import clsx from 'clsx';

interface NeumorphicToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
  className?: string;
}

const NeumorphicToggle: React.FC<NeumorphicToggleProps> = ({
  checked,
  onChange,
  label,
  disabled = false,
  className
}) => {
  const handleToggle = () => {
    if (!disabled) {
      onChange(!checked);
    }
  };

  return (
    <div className={clsx('flex items-center gap-3', className)}>
      <button
        type="button"
        className={clsx(
          'relative w-12 h-6 bg-neumorphic-bg rounded-full transition-all duration-200',
          'shadow-neumorphic-inset-sm',
          disabled && 'opacity-50 cursor-not-allowed',
          !disabled && 'cursor-pointer'
        )}
        onClick={handleToggle}
        disabled={disabled}
        role="switch"
        aria-checked={checked}
      >
        <span
          className={clsx(
            'absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-all duration-200',
            'shadow-neumorphic-sm',
            checked ? 'translate-x-6 bg-neumorphic-accent-blue' : 'bg-neumorphic-bg'
          )}
        />
        {checked && (
          <span className="absolute right-1.5 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-white/50 animate-pulse" />
        )}
      </button>
      {label && (
        <label
          className={clsx(
            'text-sm font-medium text-neumorphic-text-primary',
            !disabled && 'cursor-pointer'
          )}
          onClick={handleToggle}
        >
          {label}
        </label>
      )}
    </div>
  );
};

export default NeumorphicToggle;