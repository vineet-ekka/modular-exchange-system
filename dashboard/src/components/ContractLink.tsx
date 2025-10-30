import React from 'react';
import { getContractTradingUrl } from '../utils/exchangeUrlMapper';

interface ContractLinkProps {
  exchange: string;
  symbol: string;
  baseAsset?: string;
  isActive?: boolean;
  hoursSinceUpdate?: number;
  className?: string;
  showIcon?: boolean;
}

const ExternalLinkIcon: React.FC<{ className?: string }> = ({ className = '' }) => (
  <svg
    className={`inline-block ${className}`}
    width="12"
    height="12"
    viewBox="0 0 12 12"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M10.5 10.5H1.5V1.5H6V0H1.5C0.67 0 0 0.67 0 1.5V10.5C0 11.33 0.67 12 1.5 12H10.5C11.33 12 12 11.33 12 10.5V6H10.5V10.5ZM7.5 0V1.5H9.44L3.16 7.78L4.22 8.84L10.5 2.56V4.5H12V0H7.5Z"
      fill="currentColor"
    />
  </svg>
);

export const ContractLink: React.FC<ContractLinkProps> = ({
  exchange,
  symbol,
  baseAsset,
  isActive = true,
  hoursSinceUpdate = 0,
  className = '',
  showIcon = true,
}) => {
  const shouldShowLink = isActive && hoursSinceUpdate < 1;

  const tradingUrl = getContractTradingUrl({
    exchange,
    symbol,
    baseAsset,
  });

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  if (!shouldShowLink || !tradingUrl) {
    const tooltipText = !isActive || hoursSinceUpdate >= 1
      ? `Contract may be delisted (last seen ${hoursSinceUpdate.toFixed(1)}h ago)`
      : 'Trading link not available';

    return (
      <span
        className={`${className} text-gray-400 cursor-help`}
        title={tooltipText}
      >
        {symbol}
      </span>
    );
  }

  return (
    <a
      href={tradingUrl}
      target="_blank"
      rel="noopener noreferrer"
      onClick={handleClick}
      className={`${className} text-blue-500 hover:text-blue-700 hover:underline transition-colors duration-150 inline-flex items-center gap-1`}
      title={`Open ${symbol} on ${exchange}`}
    >
      <span>{symbol}</span>
      {showIcon && <ExternalLinkIcon className="opacity-60" />}
    </a>
  );
};

export default ContractLink;
