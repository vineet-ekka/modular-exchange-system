import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import Header from '../components/Layout/Header';
import HistoricalFundingView from '../components/Grid/HistoricalFundingView';

function HistoricalFundingPage() {
  const { asset } = useParams<{ asset: string }>();
  const navigate = useNavigate();
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // If no asset is provided, redirect to dashboard
  useEffect(() => {
    if (!asset) {
      navigate('/');
    }
  }, [asset, navigate]);

  if (!asset) {
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
            <span className="text-text-primary font-medium">{asset}</span>
          </nav>
        </div>

        {/* Historical Funding View Component */}
        <HistoricalFundingView asset={asset} onUpdate={() => setLastUpdate(new Date())} />
      </main>
    </div>
  );
}

export default HistoricalFundingPage;