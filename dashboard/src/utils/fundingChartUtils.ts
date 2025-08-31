/**
 * Funding Chart Data Processing Utilities
 * Handles forward-fill for null values and detects funding intervals
 */

export interface ProcessedDataPoint {
  timestamp: string;
  displayTime: string;
  rawTimestamp?: string;
  [contractName: string]: string | number | boolean | null | undefined;
}

export interface FundingMetadata {
  isActual: boolean;
  change: number | null;
  interval: number;
}

/**
 * Forward fills null values with the last known value
 * This creates a step function effect for funding rates
 */
export function forwardFillData(
  data: any[], 
  contractName: string
): ProcessedDataPoint[] {
  let lastKnownValue: number | null = null;
  let lastKnownAPR: number | null = null;
  
  return data.map((point, index) => {
    const currentValue = point[contractName];
    const currentAPR = point[`${contractName}_apr`];
    
    if (currentValue !== null && currentValue !== undefined) {
      // Actual data point
      const change = lastKnownAPR !== null 
        ? ((currentAPR - lastKnownAPR) / Math.abs(lastKnownAPR)) * 100 
        : null;
      
      lastKnownValue = currentValue;
      lastKnownAPR = currentAPR;
      
      return {
        ...point,
        [`${contractName}_isActual`]: true,
        [`${contractName}_change`]: change
      };
    } else {
      // Fill with last known value
      return {
        ...point,
        [contractName]: lastKnownValue,
        [`${contractName}_apr`]: lastKnownAPR,
        [`${contractName}_isActual`]: false,
        [`${contractName}_change`]: null
      };
    }
  });
}

/**
 * Detects the funding interval for a contract by analyzing the time between updates
 */
export function detectFundingInterval(
  data: any[], 
  contractName: string
): number {
  // Find consecutive actual data points and calculate interval
  const actualPoints = data.filter(p => 
    p[contractName] !== null && 
    p[contractName] !== undefined
  );
  
  if (actualPoints.length < 2) return 8; // Default to 8h if insufficient data
  
  // Calculate time difference between first two actual points
  const firstTime = new Date(actualPoints[0].rawTimestamp || actualPoints[0].timestamp);
  const secondTime = new Date(actualPoints[1].rawTimestamp || actualPoints[1].timestamp);
  const hoursDiff = Math.abs(secondTime.getTime() - firstTime.getTime()) / (1000 * 60 * 60);
  
  // Round to nearest standard interval
  if (hoursDiff <= 1.5) return 1;
  if (hoursDiff <= 3) return 2;
  if (hoursDiff <= 6) return 4;
  return 8;
}

/**
 * Finds timestamps where funding actually updates (not forward-filled values)
 */
export function findActualFundingTimes(
  data: ProcessedDataPoint[], 
  contractName: string
): string[] {
  return data
    .filter(point => point[`${contractName}_isActual`] === true)
    .map(point => point.timestamp);
}

/**
 * Calculates statistics for a contract's funding rates
 */
export function calculateContractStats(
  data: any[],
  contractName: string
): {
  avg: number;
  min: number;
  max: number;
  count: number;
} {
  const values = data
    .map(d => d[`${contractName}_apr`])
    .filter(v => v !== null && v !== undefined && typeof v === 'number') as number[];
  
  if (values.length === 0) {
    return { avg: 0, min: 0, max: 0, count: 0 };
  }
  
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const min = Math.min(...values);
  const max = Math.max(...values);
  
  return {
    avg: isNaN(avg) || !isFinite(avg) ? 0 : avg,
    min: isNaN(min) || !isFinite(min) ? 0 : min,
    max: isNaN(max) || !isFinite(max) ? 0 : max,
    count: values.length
  };
}

/**
 * Preprocesses chart data for step function visualization
 */
export function preprocessChartData(
  rawData: any[],
  contractName: string
): {
  processedData: ProcessedDataPoint[];
  fundingInterval: number;
  actualFundingTimes: string[];
} {
  if (!contractName || !rawData || rawData.length === 0) {
    return {
      processedData: rawData,
      fundingInterval: 8,
      actualFundingTimes: []
    };
  }
  
  // Forward fill nulls for step function
  const processedData = forwardFillData(rawData, contractName);
  
  // Detect funding interval
  const fundingInterval = detectFundingInterval(rawData, contractName);
  
  // Find actual funding times for reference lines
  const actualFundingTimes = findActualFundingTimes(processedData, contractName);
  
  return {
    processedData,
    fundingInterval,
    actualFundingTimes
  };
}