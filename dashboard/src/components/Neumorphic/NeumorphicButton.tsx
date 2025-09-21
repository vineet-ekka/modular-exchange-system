import React, { useState } from 'react';
import clsx from 'clsx';

interface NeumorphicButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  className?: string;
  type?: 'button' | 'submit' | 'reset';
}

const NeumorphicButton: React.FC<NeumorphicButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  className,
  type = 'button'
}) => {
  const [isPressed, setIsPressed] = useState(false);

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg'
  };

  const variantClasses = {
    primary: 'text-neumorphic-accent-blue',
    secondary: 'text-neumorphic-text-secondary',
    success: 'text-neumorphic-accent-green',
    danger: 'text-neumorphic-accent-red',
    warning: 'text-neumorphic-accent-orange'
  };

  const handleMouseDown = () => {
    if (!disabled) setIsPressed(true);
  };

  const handleMouseUp = () => {
    setIsPressed(false);
  };

  const handleMouseLeave = () => {
    setIsPressed(false);
  };

  return (
    <button
      type={type}
      className={clsx(
        'bg-neumorphic-bg rounded-lg font-medium transition-all duration-200 outline-none',
        sizeClasses[size],
        variantClasses[variant],
        isPressed ? 'shadow-neumorphic-pressed scale-95' : 'shadow-neumorphic hover:shadow-neumorphic-hover',
        disabled && 'opacity-50 cursor-not-allowed',
        !disabled && 'cursor-pointer',
        className
      )}
      onClick={onClick}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
      disabled={disabled}
    >
      {children}
    </button>
  );
};

export default NeumorphicButton;