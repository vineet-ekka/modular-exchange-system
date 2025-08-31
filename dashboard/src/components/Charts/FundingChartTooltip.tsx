import React from 'react';
import clsx from 'clsx';

interface FundingChartTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
  contractName: string;
  fundingInterval: number;
}

export const FundingChartTooltip: React.FC<FundingChartTooltipProps> = ({
  active,
  payload,
  label,
  contractName,
  fundingInterval
}) => {
  if (!active || !payload || !payload.length) return null;
  
  const data = payload[0]?.payload;
  if (!data) return null;
  
  const aprValue = data[`${contractName}_apr`];
  const isActual = data[`${contractName}_isActual`];
  const change = data[`${contractName}_change`];
  const fundingRate = data[contractName];
  
  return (
    <div className="bg-white p-3 rounded-lg border border-gray-200 shadow-lg">
      <p className="font-semibold text-gray-800 mb-2">{label}</p>
      <div className="space-y-1">
        {/* Contract Info */}
        <div className="flex justify-between gap-4">
          <span className="text-sm text-gray-600">Contract:</span>
          <span className="text-sm font-medium">
            {contractName} [{fundingInterval}h]
          </span>
        </div>
        
        {/* APR Value */}
        <div className="flex justify-between gap-4">
          <span className="text-sm text-gray-600">APR:</span>
          <span className={clsx(
            "text-sm font-medium",
            aprValue && aprValue > 0 ? 'text-green-600' : 
            aprValue && aprValue < 0 ? 'text-red-600' : 
            'text-gray-600'
          )}>
            {aprValue !== null && aprValue !== undefined 
              ? `${aprValue.toFixed(2)}%` 
              : 'N/A'}
          </span>
        </div>
        
        {/* Funding Rate */}
        {fundingRate !== null && fundingRate !== undefined && (
          <div className="flex justify-between gap-4">
            <span className="text-sm text-gray-600">Funding Rate:</span>
            <span className="text-sm font-medium">
              {(fundingRate).toFixed(4)}%
            </span>
          </div>
        )}
        
        {/* Change from Previous */}
        {change !== null && change !== undefined && (
          <div className="flex justify-between gap-4">
            <span className="text-sm text-gray-600">Change:</span>
            <span className={clsx(
              "text-sm font-medium",
              change > 0 ? 'text-green-600' : 
              change < 0 ? 'text-red-600' : 
              'text-gray-600'
            )}>
              {change > 0 ? '+' : ''}{change.toFixed(2)}%
            </span>
          </div>
        )}
        
        {/* Data Type Indicator */}
        {!isActual && (
          <div className="text-xs text-gray-500 italic mt-2 pt-2 border-t border-gray-100">
            Held value - funding occurs every {fundingInterval}h
          </div>
        )}
        {isActual && (
          <div className="text-xs text-blue-600 font-medium mt-2 pt-2 border-t border-gray-100">
            ✓ Actual funding update
          </div>
        )}
      </div>
    </div>
  );
};

export default FundingChartTooltip;