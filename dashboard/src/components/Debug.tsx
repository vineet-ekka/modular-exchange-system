import React, { useState, useEffect } from 'react';

const Debug: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<string>('Checking...');
  const [dataCount, setDataCount] = useState<number>(0);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const checkAPI = async () => {
      try {
        // Direct fetch without using the service
        const response = await fetch('http://localhost:8000/api/funding-rates?limit=5');
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        setDataCount(data.length);
        setApiStatus('Connected');
        console.log('API Data:', data);
      } catch (err) {
        setApiStatus('Failed');
        setError(err instanceof Error ? err.message : String(err));
        console.error('API Error:', err);
      }
    };

    checkAPI();
  }, []);

  return (
    <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">
      <p className="font-bold">Debug Info:</p>
      <p>API Status: {apiStatus}</p>
      <p>Data Count: {dataCount}</p>
      {error && <p className="text-red-600">Error: {error}</p>}
      <p className="text-xs mt-2">Check browser console for details</p>
    </div>
  );
};

export default Debug;