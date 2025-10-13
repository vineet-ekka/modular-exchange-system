import React, { useState, useRef, useEffect } from 'react';
import clsx from 'clsx';

interface MultiSelectOption {
  value: string;
  label: string;
  count?: number;
  color?: string;
  disabled?: boolean;
}

interface ModernMultiSelectProps {
  label?: string;
  options: MultiSelectOption[];
  value: Set<string>;
  onChange: (selected: Set<string>) => void;
  placeholder?: string;
  className?: string;
  minSelected?: number;
  size?: 'default' | 'compact';
}

const ModernMultiSelect: React.FC<ModernMultiSelectProps> = ({
  label,
  options,
  value,
  onChange,
  placeholder = 'Select options',
  className,
  minSelected = 1,
  size = 'default',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleToggle = (optionValue: string) => {
    const newSelected = new Set(value);

    if (newSelected.has(optionValue)) {
      if (newSelected.size > minSelected) {
        newSelected.delete(optionValue);
      }
    } else {
      newSelected.add(optionValue);
    }

    onChange(newSelected);
  };

  const selectedCount = value.size;
  const totalCount = options.length;

  const selectedOptions = options.filter(opt => value.has(opt.value));

  const buttonPadding = size === 'compact' ? 'px-3 py-1.5' : 'px-4 py-2.5';
  const buttonTextSize = size === 'compact' ? 'text-xs' : 'text-sm';
  const labelMargin = size === 'compact' ? 'mb-1.5' : 'mb-2';
  const optionPadding = size === 'compact' ? 'px-2.5 py-1.5' : 'px-3 py-2';
  const optionTextSize = size === 'compact' ? 'text-xs' : 'text-sm';

  return (
    <div className={clsx('relative', className)} ref={dropdownRef}>
      {label && (
        <label className={clsx('block text-sm font-medium text-text-secondary', labelMargin)}>
          {label}
        </label>
      )}

      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'w-full text-left rounded-lg border transition-all',
          'flex items-center justify-between',
          'hover:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20',
          isOpen ? 'border-primary ring-2 ring-primary/20' : 'border-border',
          buttonPadding,
          buttonTextSize
        )}
      >
        <span className="flex items-center gap-2 flex-1 min-w-0">
          {selectedCount > 0 ? (
            <>
              <span className="font-medium text-text-primary">
                {selectedCount} selected
              </span>
              <span className="text-text-tertiary">of {totalCount}</span>
            </>
          ) : (
            <span className="text-text-tertiary">{placeholder}</span>
          )}
        </span>
        <svg
          className={clsx(
            'h-5 w-5 text-text-tertiary transition-transform flex-shrink-0',
            isOpen && 'transform rotate-180'
          )}
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
      </button>

      {isOpen && (
        <div className="absolute z-50 w-full mt-2 bg-white border border-border rounded-lg shadow-lg max-h-80 overflow-y-auto">
          <div className="p-2 space-y-1">
            {options.map((option) => {
              const isSelected = value.has(option.value);
              const isDisabled = option.disabled || (isSelected && value.size <= minSelected);

              return (
                <label
                  key={option.value}
                  className={clsx(
                    'flex items-center gap-2 rounded-md cursor-pointer transition-colors',
                    optionPadding,
                    isDisabled
                      ? 'opacity-50 cursor-not-allowed'
                      : 'hover:bg-gray-50'
                  )}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => !isDisabled && handleToggle(option.value)}
                    disabled={isDisabled}
                    className={clsx(
                      'text-primary border-gray-300 rounded focus:ring-primary',
                      size === 'compact' ? 'w-3.5 h-3.5' : 'w-4 h-4'
                    )}
                  />

                  <div className="flex items-center gap-1.5 flex-1 min-w-0">
                    {option.color && (
                      <div
                        className={clsx(
                          'rounded-full flex-shrink-0',
                          size === 'compact' ? 'w-2.5 h-2.5' : 'w-3 h-3'
                        )}
                        style={{ backgroundColor: option.color }}
                      />
                    )}
                    <span className={clsx('font-medium text-text-primary truncate', optionTextSize)}>
                      {option.label}
                    </span>
                    {option.count !== undefined && (
                      <span className="text-xs text-text-tertiary flex-shrink-0">
                        ({option.count})
                      </span>
                    )}
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default ModernMultiSelect;
