import React from 'react';
import Header from '../components/Layout/Header';
import ArbitrageOpportunities from '../components/ArbitrageOpportunities';

const ArbitragePage: React.FC = () => {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="container py-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-text-primary">Arbitrage Opportunities</h1>
          <p className="text-text-secondary mt-1">Real-time cross-exchange funding rate spreads and arbitrage opportunities</p>
        </div>
        <ArbitrageOpportunities />
      </div>
    </div>
  );
};

export default ArbitragePage;