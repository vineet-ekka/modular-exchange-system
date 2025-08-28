import React, { useState } from 'react';

interface ShutdownHeaderButtonProps {
  className?: string;
}

const ShutdownHeaderButton: React.FC<ShutdownHeaderButtonProps> = ({ className = "" }) => {
  const [isShuttingDown, setIsShuttingDown] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleShutdown = async () => {
    setIsShuttingDown(true);
    
    try {
      const response = await fetch('http://localhost:8000/api/shutdown', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        await response.json(); // Consume response
        
        // Show shutdown message
        alert('Dashboard is shutting down...\n\nAll processes will be stopped.\nTo restart, run: python start.py');
        
        // Close the window after a delay
        setTimeout(() => {
          window.close();
          // Fallback if window.close() doesn't work
          window.location.href = 'about:blank';
        }, 3000);
      } else {
        alert('Failed to initiate shutdown. Please close manually.');
        setIsShuttingDown(false);
      }
    } catch (error) {
      console.error('Shutdown error:', error);
      alert('Error connecting to server. You may need to stop processes manually.');
      setIsShuttingDown(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setShowConfirm(true)}
        disabled={isShuttingDown}
        className={className || "px-3 py-1 bg-gray-700 hover:bg-gray-800 text-white rounded text-sm transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"}
        title="Shutdown Dashboard"
      >
        {isShuttingDown ? 'Shutting down...' : 'Shutdown'}
      </button>
      
      {showConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[100]">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md">
            <h2 className="text-xl font-bold text-text-primary mb-4">
              Shutdown Dashboard?
            </h2>
            <p className="text-text-secondary mb-6">
              This will stop all dashboard processes:
            </p>
            <ul className="list-disc list-inside text-sm text-text-secondary mb-6 space-y-1">
              <li>React dashboard (port 3000)</li>
              <li>API server (port 8000)</li>
              <li>Data collector</li>
              <li>Background processes</li>
            </ul>
            <p className="text-sm text-text-muted mb-6">
              PostgreSQL will remain running to preserve your data.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 text-text-secondary hover:text-text-primary transition-colors"
                disabled={isShuttingDown}
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowConfirm(false);
                  handleShutdown();
                }}
                disabled={isShuttingDown}
                className="px-4 py-2 bg-accent-red hover:bg-red-600 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isShuttingDown ? 'Shutting down...' : 'Shutdown'}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {isShuttingDown && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[90]">
          <div className="bg-white rounded-lg shadow-xl p-8 max-w-sm text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-blue mx-auto mb-4"></div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              Shutting Down Dashboard
            </h3>
            <p className="text-sm text-text-secondary">
              Stopping all processes...
            </p>
            <p className="text-xs text-text-muted mt-4">
              This window will close automatically
            </p>
          </div>
        </div>
      )}
    </>
  );
};

export default ShutdownHeaderButton;