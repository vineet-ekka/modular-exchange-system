import React from 'react';
import { LineChart, Line, ResponsiveContainer, YAxis, Tooltip } from 'recharts';

interface SparklineProps {
  data: Array<{
    time: string;
    value: number;
  }>;
  color?: string;
  height?: number;
  showTooltip?: boolean;
}

const Sparkline: React.FC<SparklineProps> = ({ 
  data, 
  color = '#10b981', 
  height = 40,
  showTooltip = true 
}) => {
  // Determine color based on trend
  const trend = data.length > 1 
    ? data[data.length - 1].value - data[0].value 
    : 0;
  
  const lineColor = trend >= 0 ? '#10b981' : '#ef4444'; // Green for positive, red for negative
  
  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload[0]) {
      return (
        <div className="bg-gray-800 border border-gray-700 rounded px-2 py-1">
          <p className="text-xs text-white">
            {`${(payload[0].value * 100).toFixed(4)}%`}
          </p>
        </div>
      );
    }
    return null;
  };
  
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <span className="text-xs text-gray-500">No data</span>
      </div>
    );
  }
  
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
        <YAxis hide domain={['dataMin', 'dataMax']} />
        {showTooltip && <Tooltip content={<CustomTooltip />} />}
        <Line 
          type="monotone" 
          dataKey="value" 
          stroke={lineColor}
          strokeWidth={1.5}
          dot={false}
          animationDuration={300}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default Sparkline;