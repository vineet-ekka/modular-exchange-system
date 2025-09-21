import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import ShutdownHeaderButton from '../ShutdownHeaderButton';

interface HeaderProps {
  lastUpdate?: Date;
}

const Header: React.FC<HeaderProps> = ({ lastUpdate }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const isSettingsPage = location.pathname === '/settings';
  const isDashboard = location.pathname === '/';
  const isArbitrage = location.pathname === '/arbitrage';

  return (
    <header className="bg-white border-b border-light-border shadow-md">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-text-primary">
              Futures Dashboard
            </h1>
            <span className="px-3 py-1 text-xs rounded-full bg-accent-green/10 text-accent-green border border-accent-green/20 animate-pulse">
              Live Data
            </span>
          </div>
          <div className="flex items-center space-x-4">
            {lastUpdate && (
              <div className="text-sm text-text-secondary">
                Last Update: {lastUpdate.toLocaleTimeString()}
              </div>
            )}
            {!isDashboard && (
              <button
                onClick={() => navigate('/')}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors shadow-sm"
              >
                Dashboard
              </button>
            )}
            {!isArbitrage && (
              <button
                onClick={() => navigate('/arbitrage')}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors shadow-sm flex items-center space-x-2"
              >
                <span>💱</span>
                <span>Arbitrage</span>
              </button>
            )}
            {!isSettingsPage && (
              <button
                onClick={() => navigate('/settings')}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors shadow-sm flex items-center space-x-2"
              >
                <span>⚙️</span>
                <span>Settings</span>
              </button>
            )}
            <ShutdownHeaderButton
              className="px-4 py-2 bg-gray-700 hover:bg-gray-800 text-white rounded-lg transition-colors shadow-sm"
            />
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;