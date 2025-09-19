import React from 'react';
import Header from '../components/Layout/Header';
import ArbitrageOpportunities from '../components/ArbitrageOpportunities';

const ArbitragePage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-100">
      <Header />
      <div className="max-w-7xl mx-auto">
        <ArbitrageOpportunities />
      </div>
    </div>
  );
};

export default ArbitragePage;