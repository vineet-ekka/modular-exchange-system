import React, { useEffect, useState } from 'react';

interface FundingData {
  asset: string;
  symbol: string;
  exchange: string;
  funding_rate: number;
  apr: number;
  funding_interval_hours: number;
  last_updated: string;
}

interface LiveFundingTickerProps {
  asset: string;
  selectedContract?: string;  // Optional: specific contract to display
}

const LiveFundingTicker: React.FC<LiveFundingTickerProps> = ({ asset, selectedContract }) => {
  const [fundingData, setFundingData] = useState<FundingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCurrentFunding = async () => {
    try {
      // If we have a specific contract selected, fetch data for that contract
      // Otherwise fall back to the asset-based endpoint
      let url = `http://localhost:8000/api/current-funding/${asset}`;
      
      if (selectedContract) {
        // Try to fetch specific contract data
        // First, fetch all funding rates and filter for the specific contract
        const allDataResponse = await fetch(`http://localhost:8000/api/funding-rates?base_asset=${asset}&limit=100`);
        if (allDataResponse.ok) {
          const allData = await allDataResponse.json();
          // Find the specific contract
          const contractData = allData.find((item: any) => item.symbol === selectedContract);
          if (contractData) {
            setFundingData({
              asset: contractData.base_asset,
              symbol: contractData.symbol,
              exchange: contractData.exchange,
              funding_rate: contractData.funding_rate,
              apr: contractData.apr,
              funding_interval_hours: contractData.funding_interval_hours,
              last_updated: contractData.last_updated
            });
            setError(null);
            setLoading(false);
            return;
          }
        }
      }
      
      // Fall back to asset-based endpoint
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch current funding');
      const data = await response.json();
      
      if (data.error) {
        setError(data.error);
      } else {
        setFundingData(data);
        setError(null);
      }
    } catch (err) {
      console.error('Error fetching current funding:', err);
      setError('Failed to load funding data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentFunding();
    // Refresh every 30 seconds
    const interval = setInterval(fetchCurrentFunding, 30000);
    return () => clearInterval(interval);
  }, [asset, selectedContract]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-4 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-32 mb-2"></div>
        <div className="h-8 bg-gray-200 rounded w-24"></div>
      </div>
    );
  }

  if (error || !fundingData) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-4">
        <div className="text-red-500 text-sm">{error || 'No data available'}</div>
      </div>
    );
  }

  const isPositive = fundingData.funding_rate >= 0;
  const rateColor = isPositive ? 'text-green-600' : 'text-red-600';
  const bgColor = isPositive ? 'bg-green-50' : 'bg-red-50';
  const borderColor = isPositive ? 'border-green-200' : 'border-red-200';

  return (
    <div className={`rounded-lg shadow-sm p-4 border ${bgColor} ${borderColor}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-600">Current Funding Rate</h3>
        <span className="text-xs text-gray-500">{fundingData.exchange}</span>
      </div>
      
      <div className="flex items-baseline space-x-3">
        <span className={`text-2xl font-bold ${rateColor}`}>
          {isPositive ? '+' : ''}{(fundingData.funding_rate * 100).toFixed(4)}%
        </span>
        <span className="text-sm text-gray-500">
          APR: {fundingData.apr.toFixed(2)}%
        </span>
      </div>
      
      <div className="mt-2 flex items-center space-x-2">
        <span className="text-xs text-gray-500">{fundingData.symbol}</span>
        <span className="text-xs text-gray-400">•</span>
        <span className="text-xs text-gray-500">
          {fundingData.funding_interval_hours}h interval
        </span>
      </div>
      
      {fundingData.last_updated && (
        <div className="mt-1 text-xs text-gray-400">
          Updated: {new Date(fundingData.last_updated).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};

export default LiveFundingTicker;