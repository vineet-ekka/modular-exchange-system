import React from 'react';
import clsx from 'clsx';

interface NeumorphicSelectProps {
  value: string | number;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  options: Array<{ value: string | number; label: string }>;
  label?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
}

const NeumorphicSelect: React.FC<NeumorphicSelectProps> = ({
  value,
  onChange,
  options,
  label,
  className,
  size = 'md',
  disabled = false
}) => {
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-5 py-3 text-lg'
  };

  return (
    <div className="flex items-center gap-2">
      {label && (
        <label className="text-sm text-neumorphic-text-secondary font-medium">
          {label}
        </label>
      )}
      <select
        value={value}
        onChange={onChange}
        disabled={disabled}
        className={clsx(
          'bg-neumorphic-bg rounded-lg text-neumorphic-text-primary',
          'shadow-neumorphic-inset-sm focus:shadow-neumorphic-inset',
          'outline-none cursor-pointer transition-all duration-200',
          'appearance-none bg-no-repeat bg-right',
          sizeClasses[size],
          disabled && 'opacity-50 cursor-not-allowed',
          className
        )}
        style={{
          backgroundImage: `url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23718096' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e")`,
          backgroundPosition: 'right 0.5rem center',
          backgroundSize: '1.5em',
          paddingRight: '2.5rem'
        }}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export default NeumorphicSelect;