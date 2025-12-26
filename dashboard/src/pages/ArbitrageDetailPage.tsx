import React, { useState, useEffect, useCallback, useMemo, memo } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import Header from '../components/Layout/Header';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { ContractArbitrageOpportunity, fetchOpportunityDetail } from '../services/arbitrage';
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
  const [error, setError] = useState<string | null>(null);

  const formatPercentage = useCallback((value?: number | null, decimals = 3) => {
    if (value === null || value === undefined) return '-';
    const percentage = value * 100;
    return `${percentage >= 0 ? '+' : ''}${percentage.toFixed(decimals)}%`;
  }, []);

  const formatPercentageValue = useCallback((value?: number | null, decimals = 3) => {
    if (value === null || value === undefined) return '-';
    return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
  }, []);

  const formatOpenInterest = useCallback((value?: number | null) => {
    if (value === null || value === undefined) return '-';
    const absValue = Math.abs(value);
    if (absValue >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (absValue >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
    if (absValue >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
  }, []);

  const getZScoreBadge = useCallback((zScore?: number | null, label = 'Z-Score') => {
    if (zScore === null || zScore === undefined) return null;
    const absZ = Math.abs(zScore);
    let variant: 'danger' | 'warning' | 'info' | 'neutral' = 'neutral';
    if (absZ >= 3) variant = 'danger';
    else if (absZ >= 2) variant = 'warning';
    else if (absZ >= 1) variant = 'info';
    return (
      <div className="flex flex-col items-center">
        <span className="text-xs text-text-tertiary mb-1">{label}</span>
        <Badge variant={variant}>
          {zScore.toFixed(2)}
        </Badge>
      </div>
    );
  }, []);

  const periodicReturns = useMemo(() => {
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
  }, [opportunity]);

  useEffect(() => {
    if (!opportunity && asset && longExchange && shortExchange) {
      setLoading(true);
      setError(null);
      fetchOpportunityDetail(asset, longExchange, shortExchange)
        .then((response) => {
          const opp = response.opportunity;
          const mapped: ContractArbitrageOpportunity = {
            asset: opp.asset,
            long_contract: opp.long_contract,
            long_exchange: opp.long_exchange,
            long_rate: opp.long_rate,
            long_apr: null,
            long_interval_hours: opp.long_interval_hours,
            long_zscore: opp.long_zscore,
            long_percentile: null,
            long_open_interest: opp.long_open_interest,
            short_contract: opp.short_contract,
            short_exchange: opp.short_exchange,
            short_rate: opp.short_rate,
            short_apr: null,
            short_interval_hours: opp.short_interval_hours,
            short_zscore: opp.short_zscore,
            short_percentile: null,
            short_open_interest: opp.short_open_interest,
            rate_spread: opp.rate_spread,
            rate_spread_pct: opp.rate_spread_pct,
            apr_spread: opp.apr_spread,
            spread_zscore: null,
            spread_mean: null,
            spread_std_dev: null,
            long_hourly_rate: opp.long_rate / opp.long_interval_hours,
            short_hourly_rate: opp.short_rate / opp.short_interval_hours,
            effective_hourly_spread: opp.effective_hourly_spread,
            sync_period_hours: (() => {
              const gcd = (a: number, b: number): number => b === 0 ? a : gcd(b, a % b);
              return (opp.long_interval_hours * opp.short_interval_hours) / gcd(opp.long_interval_hours, opp.short_interval_hours);
            })(),
            long_sync_funding: (() => {
              const gcd = (a: number, b: number): number => b === 0 ? a : gcd(b, a % b);
              const syncPeriod = (opp.long_interval_hours * opp.short_interval_hours) / gcd(opp.long_interval_hours, opp.short_interval_hours);
              return opp.long_rate * (syncPeriod / opp.long_interval_hours);
            })(),
            short_sync_funding: (() => {
              const gcd = (a: number, b: number): number => b === 0 ? a : gcd(b, a % b);
              const syncPeriod = (opp.long_interval_hours * opp.short_interval_hours) / gcd(opp.long_interval_hours, opp.short_interval_hours);
              return opp.short_rate * (syncPeriod / opp.short_interval_hours);
            })(),
            sync_period_spread: (() => {
              const gcd = (a: number, b: number): number => b === 0 ? a : gcd(b, a % b);
              const syncPeriod = (opp.long_interval_hours * opp.short_interval_hours) / gcd(opp.long_interval_hours, opp.short_interval_hours);
              const longSync = opp.long_rate * (syncPeriod / opp.long_interval_hours);
              const shortSync = opp.short_rate * (syncPeriod / opp.short_interval_hours);
              return Math.abs(longSync) + Math.abs(shortSync);
            })(),
            long_daily_funding: opp.long_rate * (24 / opp.long_interval_hours),
            short_daily_funding: opp.short_rate * (24 / opp.short_interval_hours),
            daily_spread: opp.daily_spread,
            weekly_spread: opp.daily_spread * 7,
            monthly_spread: opp.daily_spread * 30,
            quarterly_spread: opp.daily_spread * 90,
            yearly_spread: opp.daily_spread * 365,
            is_significant: false,
          };
          setOpportunity(mapped);
        })
        .catch((err) => {
          setError(err.response?.status === 404 ? 'Opportunity not found' : 'Failed to load opportunity');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [opportunity, asset, longExchange, shortExchange]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="w-full px-6 py-6">
          <Card className="bg-white border border-border shadow-sm p-8">
            <div className="text-center py-8">
              <p className="text-text-secondary">Loading opportunity...</p>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  if (error || !opportunity) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="w-full px-6 py-6">
          <Card className="bg-white border border-border shadow-sm p-8">
            <div className="text-center py-8">
              <p className="text-text-secondary mb-4">{error || 'Opportunity data not found'}</p>
              <Button variant="default" onClick={() => navigate('/arbitrage')}>
                Back to Arbitrage Opportunities
              </Button>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="w-full px-6 py-6">
        {/* Back Button and Header */}
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => navigate('/arbitrage')}
            className="mb-4"
          >
            Back to Opportunities
          </Button>
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
          <Card className="shadow-md hover:shadow-lg transition-shadow duration-200 p-6">
            <div className="text-sm text-text-secondary mb-2">Funding Rate Spread</div>
            <div className="text-2xl font-bold text-success mb-1">
              {formatPercentageValue(opportunity.rate_spread_pct)}
            </div>
            <div className="text-sm text-text-tertiary">
              Long: {formatPercentage(opportunity.long_rate)} | Short: {formatPercentage(opportunity.short_rate)}
            </div>
          </Card>

          <Card className="shadow-md hover:shadow-lg transition-shadow duration-200 p-6">
            <div className="text-sm text-text-secondary mb-2">Funding Intervals</div>
            <div className="text-2xl font-bold text-text-primary mb-1">
              {opportunity.long_interval_hours}h / {opportunity.short_interval_hours}h
            </div>
            <div className="text-sm text-text-tertiary">
              Sync Period: {opportunity.sync_period_hours}h
            </div>
          </Card>

          <Card className="shadow-md hover:shadow-lg transition-shadow duration-200 p-6">
            <div className="text-sm text-text-secondary mb-2">Statistical Significance</div>
            <div className="flex justify-around mt-2">
              {getZScoreBadge(opportunity.spread_zscore, 'Spread')}
              {getZScoreBadge(opportunity.long_zscore, 'Long')}
              {getZScoreBadge(opportunity.short_zscore, 'Short')}
            </div>
          </Card>
        </div>

        {/* Periodic Funding Returns - Compact Height */}
        <Card className="shadow-md hover:shadow-lg transition-shadow duration-200 p-4 mb-6 border-2 border-primary">
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
          <div className="mt-3 pt-2 border-t border-border-subtle text-xs text-text-tertiary text-center">
            Projected returns based on current funding rates. Actual returns may vary significantly as rates fluctuate.
          </div>
        </Card>

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
          <Card className="shadow-none border border-border bg-white p-6">
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
          </Card>

          {/* Short Position */}
          <Card className="shadow-none border border-border bg-white p-6">
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
          </Card>
        </div>

        {/* Sync Period Analysis */}
        <Card className="bg-white border border-border shadow-sm p-6 mb-6">
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
        </Card>

        {/* Spread Statistics */}
        {opportunity.spread_mean !== null && opportunity.spread_std_dev !== null && (
          <Card className="bg-white border border-border shadow-sm p-6">
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
          </Card>
        )}
      </div>
    </div>
  );
};

export default memo(ArbitrageDetailPage);