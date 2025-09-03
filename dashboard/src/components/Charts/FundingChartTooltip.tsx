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
  
  const fundingRate = data[contractName];
  const aprValue = data[`${contractName}_apr`];
  const rawTimestamp = data.rawTimestamp;
  
  // Format the funding time properly
  const fundingTime = rawTimestamp 
    ? new Date(rawTimestamp).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZone: 'UTC',
        timeZoneName: 'short'
      })
    : label;
  
  return (
    <div className="bg-white p-3 rounded-lg border border-gray-200 shadow-lg">
      <div className="space-y-2">
        {/* Funding Time */}
        <div className="border-b border-gray-100 pb-2">
          <p className="text-sm font-semibold text-gray-800">Funding Time</p>
          <p className="text-sm text-gray-600">{fundingTime}</p>
        </div>
        
        {/* Funding Rate */}
        <div className="flex justify-between gap-6">
          <span className="text-sm text-gray-600">Funding Rate:</span>
          <span className={clsx(
            "text-sm font-semibold",
            fundingRate && fundingRate > 0 ? 'text-green-600' : 
            fundingRate && fundingRate < 0 ? 'text-red-600' : 
            'text-gray-800'
          )}>
            {fundingRate !== null && fundingRate !== undefined 
              ? `${fundingRate.toFixed(4)}%` 
              : 'N/A'}
          </span>
        </div>
        
        {/* Funding Rate APR */}
        <div className="flex justify-between gap-6">
          <span className="text-sm text-gray-600">Funding Rate APR:</span>
          <span className={clsx(
            "text-sm font-semibold",
            aprValue && aprValue > 0 ? 'text-green-600' : 
            aprValue && aprValue < 0 ? 'text-red-600' : 
            'text-gray-800'
          )}>
            {aprValue !== null && aprValue !== undefined 
              ? `${aprValue.toFixed(2)}%` 
              : 'N/A'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default FundingChartTooltip;