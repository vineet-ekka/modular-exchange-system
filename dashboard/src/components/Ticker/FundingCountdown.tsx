import React, { useEffect, useState } from 'react';

interface CountdownData {
  next_funding_time: string;
  time_until_funding: {
    hours: number;
    minutes: number;
    seconds: number;
    display: string;
  };
}

interface FundingCountdownProps {
  asset: string;
  selectedContract?: string;  // Optional: specific contract to display countdown for
}

const FundingCountdown: React.FC<FundingCountdownProps> = ({ asset, selectedContract }) => {
  const [countdownData, setCountdownData] = useState<CountdownData | null>(null);
  const [currentTime, setCurrentTime] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [hasReachedZero, setHasReachedZero] = useState(false);

  const fetchCountdownData = async () => {
    try {
      // If we have a specific contract selected, fetch data for that contract
      if (selectedContract) {
        // Fetch all funding rates and filter for the specific contract
        const allDataResponse = await fetch(`http://localhost:8000/api/funding-rates?base_asset=${asset}&limit=2000`);
        if (allDataResponse.ok) {
          const allData = await allDataResponse.json();
          // Find the specific contract
          const contractData = allData.find((item: any) => item.symbol === selectedContract);
          
          if (contractData) {
            // Calculate next funding time based on contract's specific interval
            const now = new Date();
            const nowUTC = new Date(now.toISOString());
            const fundingInterval = contractData.funding_interval_hours || 8;
            
            // Calculate next funding hour
            const currentHour = nowUTC.getUTCHours();
            const nextFundingHour = Math.ceil(currentHour / fundingInterval) * fundingInterval;
            
            let nextFundingTime;
            if (nextFundingHour >= 24) {
              // Next funding is tomorrow
              nextFundingTime = new Date(Date.UTC(
                nowUTC.getUTCFullYear(),
                nowUTC.getUTCMonth(),
                nowUTC.getUTCDate() + 1,
                nextFundingHour % 24,
                0, 0, 0
              ));
            } else {
              // Next funding is today
              nextFundingTime = new Date(Date.UTC(
                nowUTC.getUTCFullYear(),
                nowUTC.getUTCMonth(),
                nowUTC.getUTCDate(),
                nextFundingHour,
                0, 0, 0
              ));
            }
            
            // Calculate time until funding
            const diff = nextFundingTime.getTime() - nowUTC.getTime();
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);
            
            setCountdownData({
              next_funding_time: nextFundingTime.toISOString(),
              time_until_funding: {
                hours,
                minutes,
                seconds,
                display: `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
              }
            });
            setHasReachedZero(false);  // Reset the flag when we get new data
            setLoading(false);
            return;
          }
        }
      }
      
      // Fall back to asset-based endpoint if no contract selected or contract fetch failed
      const response = await fetch(`http://localhost:8000/api/current-funding/${asset}`);
      if (!response.ok) throw new Error('Failed to fetch countdown data');
      const data = await response.json();
      
      if (!data.error && data.next_funding_time) {
        setCountdownData({
          next_funding_time: data.next_funding_time,
          time_until_funding: data.time_until_funding
        });
        setHasReachedZero(false);  // Reset the flag when we get new data
      }
    } catch (err) {
      console.error('Error fetching countdown data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCountdownData();
    // Refresh countdown data every 30 seconds
    const dataInterval = setInterval(fetchCountdownData, 30000);
    
    return () => clearInterval(dataInterval);
  }, [asset, selectedContract]);

  useEffect(() => {
    if (!countdownData) return;

    // Update countdown every second
    const updateCountdown = () => {
      const now = new Date();
      const nextFunding = new Date(countdownData.next_funding_time);
      const diff = nextFunding.getTime() - now.getTime();

      if (diff > 0) {
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);
        
        setCurrentTime(`${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`);
        // Reset the flag if we're back to positive time
        if (hasReachedZero) {
          setHasReachedZero(false);
        }
      } else if (!hasReachedZero) {
        // When countdown reaches zero for the first time
        setCurrentTime('00:00:00');
        setHasReachedZero(true);
        // Fetch new data immediately
        fetchCountdownData();
      } else {
        // Keep showing 00:00:00 while waiting for new data
        setCurrentTime('00:00:00');
      }
    };

    updateCountdown();
    const countInterval = setInterval(updateCountdown, 1000);

    return () => clearInterval(countInterval);
  }, [countdownData, hasReachedZero]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-4 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-32 mb-2"></div>
        <div className="h-8 bg-gray-200 rounded w-24"></div>
      </div>
    );
  }

  if (!countdownData) {
    return null;
  }

  const timeLeft = currentTime || countdownData.time_until_funding.display;
  const [hours] = timeLeft.split(':');
  const hoursNum = parseInt(hours);
  
  // Determine urgency colors
  const isUrgent = hoursNum === 0;
  const isWarning = hoursNum <= 1;
  
  let bgColor = 'bg-blue-50';
  let borderColor = 'border-blue-200';
  let textColor = 'text-blue-600';
  
  if (isUrgent) {
    bgColor = 'bg-red-50';
    borderColor = 'border-red-200';
    textColor = 'text-red-600';
  } else if (isWarning) {
    bgColor = 'bg-yellow-50';
    borderColor = 'border-yellow-200';
    textColor = 'text-yellow-600';
  }

  return (
    <div className={`rounded-lg shadow-sm p-4 border ${bgColor} ${borderColor}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-600">Next Funding In</h3>
        {isUrgent && (
          <span className="text-xs text-red-500 font-medium animate-pulse">
            SOON
          </span>
        )}
      </div>
      
      <div className="flex items-baseline space-x-2">
        <span className={`text-2xl font-bold font-mono ${textColor}`}>
          {timeLeft}
        </span>
      </div>
      
      <div className="mt-2 text-xs text-gray-500">
        Next funding: {new Date(countdownData.next_funding_time).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
          timeZoneName: 'short'
        })}
      </div>
      
      {isUrgent && (
        <div className="mt-2 text-xs text-red-500 font-medium">
          Funding payment will occur in less than 1 hour
        </div>
      )}
    </div>
  );
};

export default FundingCountdown;