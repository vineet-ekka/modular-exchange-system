import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import HistoricalFundingPage from './pages/HistoricalFundingPage';
import SettingsPage from './pages/SettingsPage';
import BackfillProgress from './components/BackfillProgress';

function App() {
  console.log('App component is rendering');
  return (
    <Router>
      <BackfillProgress />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        {/* New contract-specific routes */}
        <Route path="/historical/:exchange/:symbol" element={<HistoricalFundingPage />} />
        {/* Keep old routes for backward compatibility */}
        <Route path="/historical/:asset" element={<HistoricalFundingPage />} />
        <Route path="/asset/:asset" element={<HistoricalFundingPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Router>
  );
}

export default App;