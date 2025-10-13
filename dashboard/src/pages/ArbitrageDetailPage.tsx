import React, { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import Header from '../components/Layout/Header';
import { ModernCard, ModernButton, ModernBadge } from '../components/Modern';
import { ContractArbitrageOpportunity } from '../services/arbitrage';
import ArbitrageHistoricalChart from '../components/Charts/ArbitrageHistoricalChart';
import clsx from 'clsx';

const ArbitrageDetailPage: React.FC = () => {
  const { asset, longExchange, shortExchange } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [opportunity, setOpportunity] = useState<ContractArbitrageOpportunity | null>(
    location.state?.opportunity || null
  );
  const [loading, setLoading] = useState(!opportunity);

  const formatPercentage = (value?: number | null, decimals = 3) => {
    if (value === null || value === undefined) return '-';
    const percentage = value * 100;
    return `${percentage >= 0 ? '+' : ''}${percentage.toFixed(decimals)}%`;
  };

  const formatPercentageValue = (value?: number | null, decimals = 3) => {
    if (value === null || value === undefined) return '-';
    return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
  };

  const formatOpenInterest = (value?: number | null) => {
    if (value === null || value === undefined) return '-';
    const absValue = Math.abs(value);
    if (absValue >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (absValue >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
    if (absValue >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
  };

  const getZScoreBadge = (zScore?: number | null, label = 'Z-Score') => {
    if (zScore === null || zScore === undefined) return null;
    const absZ = Math.abs(zScore);
    let variant: 'danger' | 'warning' | 'info' | 'neutral' = 'neutral';
    if (absZ >= 3) variant = 'danger';
    else if (absZ >= 2) variant = 'warning';
    else if (absZ >= 1) variant = 'info';
    return (
      <div className="flex flex-col items-center">
        <span className="text-xs text-text-tertiary mb-1">{label}</span>
        <ModernBadge variant={variant} size="md">
          {zScore.toFixed(2)}
        </ModernBadge>
      </div>
    );
  };

  const calculatePeriodicReturns = () => {
    if (!opportunity) return [];
    const dailySpread = opportunity.daily_spread || 0;
    return [
      { period: '1 Hour', value: opportunity.effective_hourly_spread, description: 'Effective hourly funding spread' },
      { period: '1 Day', value: dailySpread, description: '24-hour cumulative funding' },
      { period: '7 Days', value: dailySpread * 7, description: 'Weekly cumulative funding' },
      { period: '30 Days', value: dailySpread * 30, description: 'Monthly cumulative funding' },
      { period: '90 Days', value: dailySpread * 90, description: 'Quarterly cumulative funding' },
      { period: '1 Year', value: dailySpread * 365, description: 'Annual cumulative funding' }
    ];
  };

  useEffect(() => {
    if (!opportunity && asset && longExchange && shortExchange) {
      // TODO: Fetch opportunity data from API if not passed through state
      setLoading(false);
    }
  }, [opportunity, asset, longExchange, shortExchange]);

  if (!opportunity) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="w-full px-2 py-6">
          <ModernCard variant="default" padding="xl">
            <div className="text-center py-8">
              <p className="text-text-secondary mb-4">Opportunity data not found</p>
              <ModernButton variant="primary" onClick={() => navigate('/arbitrage')}>
                Back to Arbitrage Opportunities
              </ModernButton>
            </div>
          </ModernCard>
        </div>
      </div>
    );
  }

  const periodicReturns = calculatePeriodicReturns();

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="w-full px-2 py-6">
        {/* Back Button and Header */}
        <div className="mb-6">
          <ModernButton
            variant="ghost"
            onClick={() => navigate('/arbitrage')}
            className="mb-4"
          >
            ← Back to Opportunities
          </ModernButton>
          <div>
            <h1 className="text-3xl font-bold text-text-primary mb-2">
              {opportunity.asset} Arbitrage Opportunity
            </h1>
            <p className="text-lg text-text-secondary">
              {opportunity.long_exchange} (Long) ↔ {opportunity.short_exchange} (Short)
            </p>
          </div>
        </div>

        {/* Key Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <ModernCard variant="elevated" padding="lg">
            <div className="text-sm text-text-secondary mb-2">Funding Rate Spread</div>
            <div className="text-2xl font-bold text-success mb-1">
              {formatPercentageValue(opportunity.rate_spread_pct)}
            </div>
            <div className="text-sm text-text-tertiary">
              Long: {formatPercentage(opportunity.long_rate)} | Short: {formatPercentage(opportunity.short_rate)}
            </div>
          </ModernCard>

          <ModernCard variant="elevated" padding="lg">
            <div className="text-sm text-text-secondary mb-2">Funding Intervals</div>
            <div className="text-2xl font-bold text-text-primary mb-1">
              {opportunity.long_interval_hours}h / {opportunity.short_interval_hours}h
            </div>
            <div className="text-sm text-text-tertiary">
              Sync Period: {opportunity.sync_period_hours}h
            </div>
          </ModernCard>

          <ModernCard variant="elevated" padding="lg">
            <div className="text-sm text-text-secondary mb-2">Statistical Significance</div>
            <div className="flex justify-around mt-2">
              {getZScoreBadge(opportunity.spread_zscore, 'Spread')}
              {getZScoreBadge(opportunity.long_zscore, 'Long')}
              {getZScoreBadge(opportunity.short_zscore, 'Short')}
            </div>
          </ModernCard>
        </div>

        {/* Periodic Funding Returns - Compact Height */}
        <ModernCard variant="elevated" padding="md" className="mb-6 border-2 border-primary">
          <h2 className="text-lg font-bold text-text-primary mb-2">
            Periodic Funding Returns
          </h2>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            {periodicReturns.map((item) => (
              <div key={item.period} className="text-center">
                <div className="text-xs text-text-secondary">{item.period}</div>
                <div className={clsx(
                  'text-xl font-bold',
                  item.value >= 0 ? 'text-success' : 'text-danger'
                )}>
                  {formatPercentage(item.value, 2)}
                </div>
                <div className="text-xs text-text-tertiary opacity-75">{item.description}</div>
              </div>
            ))}
          </div>
        </ModernCard>

        {/* Historical Funding Chart - Moved Below Periodic Returns */}
        <ArbitrageHistoricalChart
          longExchange={opportunity.long_exchange}
          longContract={opportunity.long_contract}
          shortExchange={opportunity.short_exchange}
          shortContract={opportunity.short_contract}
          asset={opportunity.asset}
          longIntervalHours={opportunity.long_interval_hours}
          shortIntervalHours={opportunity.short_interval_hours}
        />

        {/* Position Details Side by Side */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Long Position */}
          <ModernCard variant="flat" padding="lg">
            <h3 className="text-lg font-bold text-text-primary mb-4">
              Long Position Details
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-text-secondary">Exchange</span>
                <span className="font-medium">{opportunity.long_exchange}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Contract</span>
                <span className="font-mono">{opportunity.long_contract}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Funding Rate</span>
                <span className={clsx(
                  'font-bold',
                  opportunity.long_rate < 0 ? 'text-success' : 'text-danger'
                )}>
                  {formatPercentage(opportunity.long_rate)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">APR</span>
                <span>{formatPercentageValue(opportunity.long_apr, 2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Interval</span>
                <span>{opportunity.long_interval_hours} hours</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Open Interest</span>
                <span>{formatOpenInterest(opportunity.long_open_interest)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Z-Score</span>
                <span>{opportunity.long_zscore?.toFixed(2) || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Percentile</span>
                <span>{opportunity.long_percentile?.toFixed(1) || '-'}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Daily Funding</span>
                <span className={clsx(
                  'font-bold',
                  opportunity.long_daily_funding < 0 ? 'text-success' : 'text-danger'
                )}>
                  {formatPercentage(opportunity.long_daily_funding)}
                </span>
              </div>
            </div>
          </ModernCard>

          {/* Short Position */}
          <ModernCard variant="flat" padding="lg">
            <h3 className="text-lg font-bold text-text-primary mb-4">
              Short Position Details
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-text-secondary">Exchange</span>
                <span className="font-medium">{opportunity.short_exchange}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Contract</span>
                <span className="font-mono">{opportunity.short_contract}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Funding Rate</span>
                <span className={clsx(
                  'font-bold',
                  opportunity.short_rate > 0 ? 'text-success' : 'text-danger'
                )}>
                  {formatPercentage(opportunity.short_rate)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">APR</span>
                <span>{formatPercentageValue(opportunity.short_apr, 2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Interval</span>
                <span>{opportunity.short_interval_hours} hours</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Open Interest</span>
                <span>{formatOpenInterest(opportunity.short_open_interest)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Z-Score</span>
                <span>{opportunity.short_zscore?.toFixed(2) || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Percentile</span>
                <span>{opportunity.short_percentile?.toFixed(1) || '-'}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Daily Funding</span>
                <span className={clsx(
                  'font-bold',
                  opportunity.short_daily_funding > 0 ? 'text-success' : 'text-danger'
                )}>
                  {formatPercentage(opportunity.short_daily_funding)}
                </span>
              </div>
            </div>
          </ModernCard>
        </div>

        {/* Sync Period Analysis */}
        <ModernCard variant="default" padding="lg" className="mb-6">
          <h3 className="text-lg font-bold text-text-primary mb-4">
            Synchronization Period Analysis
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <div className="text-sm text-text-secondary mb-1">Sync Period</div>
              <div className="text-xl font-bold">{opportunity.sync_period_hours} hours</div>
              <div className="text-xs text-text-tertiary">
                Both positions complete full cycles
              </div>
            </div>
            <div>
              <div className="text-sm text-text-secondary mb-1">Long Funding</div>
              <div className="text-xl font-bold">{formatPercentage(opportunity.long_sync_funding)}</div>
              <div className="text-xs text-text-tertiary">
                Over {opportunity.sync_period_hours}h period
              </div>
            </div>
            <div>
              <div className="text-sm text-text-secondary mb-1">Short Funding</div>
              <div className="text-xl font-bold">{formatPercentage(opportunity.short_sync_funding)}</div>
              <div className="text-xs text-text-tertiary">
                Over {opportunity.sync_period_hours}h period
              </div>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-border-subtle">
            <div className="flex justify-between items-center">
              <span className="text-text-secondary">Net Sync Period Spread</span>
              <span className="text-2xl font-bold text-warning">
                {formatPercentage(opportunity.sync_period_spread)}
              </span>
            </div>
          </div>
        </ModernCard>

        {/* Spread Statistics */}
        {opportunity.spread_mean !== null && opportunity.spread_std_dev !== null && (
          <ModernCard variant="default" padding="lg">
            <h3 className="text-lg font-bold text-text-primary mb-4">
              Historical Spread Statistics
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <div className="text-sm text-text-secondary mb-1">Mean APR Spread (30d)</div>
                <div className="text-xl font-bold">{opportunity.spread_mean.toFixed(2)}%</div>
              </div>
              <div>
                <div className="text-sm text-text-secondary mb-1">Std Deviation</div>
                <div className="text-xl font-bold">{opportunity.spread_std_dev.toFixed(2)}%</div>
              </div>
              <div>
                <div className="text-sm text-text-secondary mb-1">Current Z-Score</div>
                <div className="text-xl font-bold">{opportunity.spread_zscore?.toFixed(2) || '-'}</div>
                <div className="text-xs text-text-tertiary">
                  {opportunity.spread_zscore && Math.abs(opportunity.spread_zscore) > 2
                    ? 'Statistically significant deviation'
                    : 'Within normal range'}
                </div>
              </div>
            </div>
          </ModernCard>
        )}
      </div>
    </div>
  );
};

export default ArbitrageDetailPage;