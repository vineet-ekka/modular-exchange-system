import React from 'react';

interface HeaderProps {
  lastUpdate?: Date;
}

const Header: React.FC<HeaderProps> = ({ lastUpdate }) => {
  return (
    <header className="bg-gray-900 border-b border-gray-800 shadow-lg">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-white">
              Exchange Funding Rates Dashboard
            </h1>
            <span className="px-3 py-1 text-xs rounded-full bg-green-500/20 text-green-400 animate-pulse">
              LIVE
            </span>
          </div>
          <div className="flex items-center space-x-4">
            {lastUpdate && (
              <div className="text-sm text-gray-400">
                Last Update: {lastUpdate.toLocaleTimeString()}
              </div>
            )}
            <button 
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;