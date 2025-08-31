import React, { useState, useEffect } from 'react';

interface BackfillStatus {
  running: boolean;
  progress: number;
  message: string;
  symbols_processed?: number;
  total_symbols?: number;
  completed: boolean;
  error?: boolean;
}

const BackfillProgress: React.FC = () => {
  const [status, setStatus] = useState<BackfillStatus | null>(null);
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const checkBackfillStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/backfill-status');
        const data: BackfillStatus = await response.json();
        
        // Stop polling if progress is 100% regardless of completed flag
        if (data.progress >= 100) {
          setStatus({
            ...data,
            running: false,
            completed: true
          });
          // Hide after 3 seconds
          setTimeout(() => {
            setIsVisible(false);
          }, 3000);
          return; // Stop checking
        }
        
        // Show the indicator if backfill is running
        if (data.running) {
          setIsVisible(true);
        }
        
        // Hide the indicator if backfill is complete
        if (data.completed && !data.running) {
          // Keep it visible for 3 seconds after completion
          setTimeout(() => {
            setIsVisible(false);
          }, 3000);
        }
        
        setStatus(data);
      } catch (error) {
        console.error('Error fetching backfill status:', error);
        setIsVisible(false); // Hide on error to prevent continuous polling
      }
    };

    // Initial check
    checkBackfillStatus();

    // Only set interval if we should be checking
    let interval: NodeJS.Timeout | undefined;
    if (isVisible && (!status || (status.progress < 100 && status.running))) {
      // Use longer interval after 50% progress
      const pollInterval = status?.progress && status.progress > 50 ? 15000 : 5000;
      interval = setInterval(checkBackfillStatus, pollInterval);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isVisible, status?.progress, status?.running]);

  // Don't render if not visible or no status
  if (!isVisible || !status) {
    return null;
  }
  
  // Only hide if completed AND not running (to handle transition)
  if (!status.running && status.completed && status.progress === 100) {
    return null;
  }

  const progressPercentage = Math.min(100, Math.max(0, status.progress));
  
  return (
    <div className="fixed bottom-4 right-4 bg-white rounded-lg shadow-lg border border-light-border p-4 max-w-sm z-50">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <div className="mr-3">
            {status.running ? (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-accent-blue"></div>
            ) : status.completed ? (
              <svg className="w-5 h-5 text-accent-green" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-accent-red" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-primary">
              Historical Data Backfill
            </h3>
            <p className="text-xs text-text-secondary mt-1">
              {status.message}
            </p>
          </div>
        </div>
        <button
          onClick={() => setIsVisible(false)}
          className="ml-4 text-text-muted hover:text-text-secondary transition-colors"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>
      
      {/* Progress bar */}
      <div className="mt-3">
        <div className="flex justify-between text-xs text-text-secondary mb-1">
          <span>Progress</span>
          <span>{progressPercentage.toFixed(0)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div 
            className={`h-full rounded-full transition-all duration-500 ${
              status.error ? 'bg-accent-red' :
              status.completed ? 'bg-accent-green' :
              'bg-accent-blue'
            }`}
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>
      
      {/* Additional info if available */}
      {status.symbols_processed !== undefined && status.total_symbols !== undefined && (
        <div className="mt-2 text-xs text-text-muted">
          Processing: {status.symbols_processed} / {status.total_symbols} symbols
        </div>
      )}
      
      {/* Estimated time */}
      {status.running && !status.error && (
        <div className="mt-2 text-xs text-text-muted">
          Estimated time remaining: ~{Math.ceil((100 - progressPercentage) * 0.05)} minutes
        </div>
      )}
    </div>
  );
};

export default BackfillProgress;