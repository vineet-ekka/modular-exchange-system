import React from 'react';
import clsx from 'clsx';

interface ModernButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  ripple?: boolean;
}

const ModernButton: React.FC<ModernButtonProps> = ({
  children,
  className,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  loading = false,
  disabled = false,
  icon,
  iconPosition = 'left',
  ripple = true,
  onClick,
  ...props
}) => {
  const [rippleEffect, setRippleEffect] = React.useState<{ x: number; y: number; show: boolean }>({
    x: 0,
    y: 0,
    show: false,
  });

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (ripple && !disabled && !loading) {
      const rect = e.currentTarget.getBoundingClientRect();
      setRippleEffect({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        show: true,
      });
      setTimeout(() => setRippleEffect(prev => ({ ...prev, show: false })), 600);
    }
    onClick?.(e);
  };

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  const variantClasses = {
    primary: 'bg-primary text-white hover:bg-primary-600 active:bg-primary-700 shadow-sm hover:shadow-md',
    secondary: 'bg-gray-100 text-text-primary hover:bg-gray-200 active:bg-gray-300',
    ghost: 'bg-transparent text-text-primary hover:bg-gray-100 active:bg-gray-200',
    danger: 'bg-danger text-white hover:bg-danger-600 active:bg-danger-700 shadow-sm hover:shadow-md',
    success: 'bg-success text-white hover:bg-success-600 active:bg-success-700 shadow-sm hover:shadow-md',
  };

  return (
    <button
      className={clsx(
        'relative inline-flex items-center justify-center rounded-md font-medium transition-all duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
        'disabled:pointer-events-none disabled:opacity-50',
        sizeClasses[size],
        variantClasses[variant],
        {
          'w-full': fullWidth,
          'overflow-hidden': ripple,
        },
        className
      )}
      disabled={disabled || loading}
      onClick={handleClick}
      {...props}
    >
      {ripple && rippleEffect.show && (
        <span
          className="absolute rounded-full bg-white/30 animate-ping"
          style={{
            left: rippleEffect.x - 20,
            top: rippleEffect.y - 20,
            width: 40,
            height: 40,
          }}
        />
      )}

      {loading && (
        <svg
          className="animate-spin -ml-1 mr-2 h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}

      {icon && iconPosition === 'left' && !loading && (
        <span className="mr-2">{icon}</span>
      )}

      <span>{children}</span>

      {icon && iconPosition === 'right' && !loading && (
        <span className="ml-2">{icon}</span>
      )}
    </button>
  );
};

export default ModernButton;