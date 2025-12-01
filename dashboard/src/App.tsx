import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Skeleton } from './components/ui/skeleton';
import BackfillProgress from './components/BackfillProgress';
import ErrorBoundary from './components/ErrorBoundary';

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const HistoricalFundingPage = lazy(() => import('./pages/HistoricalFundingPage'));
const ArbitragePage = lazy(() => import('./pages/ArbitragePage'));
const ArbitrageDetailPage = lazy(() => import('./pages/ArbitrageDetailPage'));
const LandingPage = lazy(() => import('./pages/LandingPage'));

const PageLoadingFallback = () => (
  <div className="container mx-auto p-8 space-y-4">
    <Skeleton className="h-12 w-64" />
    <Skeleton className="h-96 w-full" />
    <div className="grid grid-cols-3 gap-4">
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-32 w-full" />
    </div>
  </div>
);

function App() {
  return (
    <Router>
      <ErrorBoundary>
        <BackfillProgress />
        <Suspense fallback={<PageLoadingFallback />}>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/landing" element={<LandingPage />} />
            <Route path="/arbitrage" element={<ArbitragePage />} />
            <Route path="/arbitrage/:asset/:longExchange/:shortExchange" element={<ArbitrageDetailPage />} />
            <Route path="/historical/:exchange/:symbol" element={<HistoricalFundingPage />} />
            <Route path="/historical/:asset" element={<HistoricalFundingPage />} />
            <Route path="/asset/:asset" element={<HistoricalFundingPage />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </Router>
  );
}

export default App;