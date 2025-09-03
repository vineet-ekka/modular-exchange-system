import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import Header from '../components/Layout/Header';
import HistoricalFundingViewContract from '../components/Grid/HistoricalFundingViewContract';

function HistoricalFundingPage() {
  const { asset, exchange, symbol } = useParams<{ asset?: string; exchange?: string; symbol?: string }>();
  const navigate = useNavigate();
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Determine if this is asset-based or contract-based routing
  const isContractView = !!(exchange && symbol);

  // If no params provided, redirect to dashboard
  useEffect(() => {
    if (!asset && !isContractView) {
      navigate('/');
    }
  }, [asset, isContractView, navigate]);

  if (!asset && !isContractView) {
    return null;
  }

  return (
    <div className="min-h-screen bg-light-bg">
      <Header lastUpdate={lastUpdate} />
      
      <main className="p-6">
        {/* Breadcrumb Navigation */}
        <div className="mb-4">
          <nav className="flex items-center space-x-2 text-sm">
            <Link 
              to="/" 
              className="text-text-secondary hover:text-text-primary transition-colors"
            >
              Dashboard
            </Link>
            <span className="text-text-muted">/</span>
            {isContractView ? (
              <>
                <span className="text-text-secondary">{exchange}</span>
                <span className="text-text-muted">/</span>
                <span className="text-text-primary font-medium">{symbol}</span>
              </>
            ) : (
              <span className="text-text-primary font-medium">{asset}</span>
            )}
          </nav>
        </div>

        {/* Historical Funding View Component */}
        <HistoricalFundingViewContract 
          asset={asset} 
          exchange={exchange}
          symbol={symbol}
          isContractView={isContractView}
          onUpdate={() => setLastUpdate(new Date())} 
        />
      </main>
    </div>
  );
}

export default HistoricalFundingPage;