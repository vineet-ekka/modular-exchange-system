import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import HistoricalFundingPage from './pages/HistoricalFundingPage';
import ArbitragePage from './pages/ArbitragePage';
import ArbitrageDetailPage from './pages/ArbitrageDetailPage';
import BackfillProgress from './components/BackfillProgress';

function App() {
  console.log('App component is rendering');
  return (
    <Router>
      <BackfillProgress />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/arbitrage" element={<ArbitragePage />} />
        <Route path="/arbitrage/:asset/:longExchange/:shortExchange" element={<ArbitrageDetailPage />} />
        {/* New contract-specific routes */}
        <Route path="/historical/:exchange/:symbol" element={<HistoricalFundingPage />} />
        {/* Keep old routes for backward compatibility */}
        <Route path="/historical/:asset" element={<HistoricalFundingPage />} />
        <Route path="/asset/:asset" element={<HistoricalFundingPage />} />
      </Routes>
    </Router>
  );
}

export default App;