import { useState, useMemo } from 'react';
import { useMerchantDashboard } from '../../hooks/queries';
import { DateRangePicker } from '../../components/common/DateRangePicker';
import { StatusBadge } from '../../components/common/StatusBadge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { KpiCard } from '../../components/common/KpiCard';

import { MerchantRevenueCard } from './MerchantRevenueCard';
import { MerchantFunnelCard } from './MerchantFunnelCard';
import { MerchantShopperBehaviorCard } from './MerchantShopperBehaviorCard';
import { MerchantAggregateJourneysCard } from './MerchantAggregateJourneysCard';
import { MerchantMetricsTrend } from './MerchantMetricsTrend';

import { MerchantHealthCard } from './MerchantHealthCard';
import { MerchantJourneyTimeline } from './MerchantJourneyTimeline';
import { MerchantProfileCard } from './MerchantProfileCard';
import { MerchantDetails } from './MerchantDetails';
import { MerchantFeatures } from './MerchantFeatures';

import { MerchantCampaigns } from './MerchantCampaigns';
import { MerchantShoppers } from './MerchantShoppers';
import { MerchantOrders } from './MerchantOrders';

type TabKey = 'overview' | 'health' | 'journey' | 'profile' | 'activity';

interface MerchantOverviewProps {
  merchantId: string;
}

export function MerchantOverview({ merchantId }: MerchantOverviewProps) {
  const initialDates = useMemo(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    return {
      startDate: start.toISOString().split('T')[0],
      endDate: end.toISOString().split('T')[0],
    };
  }, []);

  const [dateRange, setDateRange] = useState(initialDates);
  const [activeTab, setActiveTab] = useState<TabKey>('overview');

  const { data, isLoading, isError, error, refetch } = useMerchantDashboard(
    merchantId,
    dateRange.startDate,
    dateRange.endDate
  );

  if (isLoading) {
    return (
      <div className="bg-white p-12 rounded-lg shadow flex items-center justify-center min-h-[400px]">
        <LoadingSpinner message="Loading merchant intelligence overview..." />
      </div>
    );
  }

  if (isError || !data) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to load merchant overview.';
    return (
      <div className="bg-white p-8 rounded-lg shadow">
        <ErrorMessage message={errorMessage} retry={() => refetch()} />
      </div>
    );
  }

  const { merchant, health, summary, revenue, funnel, journeys, behavior } = data;

  const tabs: { key: TabKey; label: string; badge?: string }[] = [
    { key: 'overview', label: 'Overview & Intelligence' },
    {
      key: 'health',
      label: 'Health & Risk',
      badge: health?.health_status ? health.health_status.replace(/_/g, ' ') : undefined,
    },
    { key: 'journey', label: 'Lifecycle Journey' },
    { key: 'profile', label: 'Profile & Features' },
    { key: 'activity', label: 'Recent Activity' },
  ];

  return (
    <div className="space-y-6">
      {/* Merchant Header Bar */}
      <div className="bg-white p-6 rounded-lg shadow border-l-4 border-indigo-600 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-gray-900">{merchant.merchant_name}</h2>
            <StatusBadge status={merchant.app_install_status} type="install" />
            {merchant.active_subscription && (
              <span className="text-xs font-medium bg-indigo-50 text-indigo-700 px-2.5 py-0.5 rounded-full border border-indigo-200">
                Plan: {merchant.active_subscription.plan_name}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-1 flex flex-wrap gap-x-4 gap-y-1">
            <span>Store ID: <strong className="font-mono text-gray-700">{merchant.shopify_store_id}</strong></span>
            <span>Email: <strong className="text-gray-700">{merchant.email}</strong></span>
            <span>Currency: <strong className="text-gray-700">{merchant.store_currency}</strong></span>
          </p>
        </div>

        <DateRangePicker
          startDate={dateRange.startDate}
          endDate={dateRange.endDate}
          onChange={setDateRange}
        />
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 bg-white px-4 rounded-t-lg shadow-xs">
        <nav className="-mb-px flex space-x-6 overflow-x-auto" aria-label="Tabs">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors focus:outline-none ${
                  isActive
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span>{tab.label}</span>
                {tab.badge && (
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                      tab.badge === 'HEALTHY'
                        ? 'bg-emerald-100 text-emerald-800'
                        : tab.badge === 'NEEDS ATTENTION'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Contents */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <KpiCard
              title="Revenue"
              value={new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: merchant.store_currency || 'USD',
              }).format(revenue.total_revenue)}
              trend={
                revenue.prior_period_comparison?.revenue_growth_pct !== null &&
                revenue.prior_period_comparison?.revenue_growth_pct !== undefined
                  ? {
                      value: `${revenue.prior_period_comparison.revenue_growth_pct >= 0 ? '+' : ''}${(revenue.prior_period_comparison.revenue_growth_pct * 100).toFixed(1)}%`,
                      isPositive: revenue.prior_period_comparison.revenue_growth_pct >= 0,
                    }
                  : undefined
              }
            />
            <KpiCard
              title="Total Orders"
              value={revenue.total_orders.toLocaleString()}
              trend={
                revenue.prior_period_comparison?.order_growth_pct !== null &&
                revenue.prior_period_comparison?.order_growth_pct !== undefined
                  ? {
                      value: `${revenue.prior_period_comparison.order_growth_pct >= 0 ? '+' : ''}${(revenue.prior_period_comparison.order_growth_pct * 100).toFixed(1)}%`,
                      isPositive: revenue.prior_period_comparison.order_growth_pct >= 0,
                    }
                  : undefined
              }
            />
            <KpiCard
              title="Average Order Value"
              value={new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: merchant.store_currency || 'USD',
              }).format(revenue.average_order_value)}
              trend={
                revenue.prior_period_comparison?.aov_growth_pct !== null &&
                revenue.prior_period_comparison?.aov_growth_pct !== undefined
                  ? {
                      value: `${revenue.prior_period_comparison.aov_growth_pct >= 0 ? '+' : ''}${(revenue.prior_period_comparison.aov_growth_pct * 100).toFixed(1)}%`,
                      isPositive: revenue.prior_period_comparison.aov_growth_pct >= 0,
                    }
                  : undefined
              }
            />
            <KpiCard
              title="Conversion Rate"
              value={`${(summary.conversion_rate * 100).toFixed(2)}%`}
            />
          </div>

          {/* Revenue & Funnel Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <MerchantRevenueCard revenue={revenue} />
            <MerchantFunnelCard funnel={funnel} />
          </div>

          {/* Shopper Behavior & Aggregate Journeys */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <MerchantShopperBehaviorCard behavior={behavior} />
            <MerchantAggregateJourneysCard journeys={journeys} />
          </div>

          {/* Metric Growth Trend Chart */}
          <MerchantMetricsTrend
            merchantId={merchantId}
            startDate={dateRange.startDate}
            endDate={dateRange.endDate}
          />
        </div>
      )}

      {activeTab === 'health' && (
        <div className="space-y-6">
          <MerchantHealthCard merchantId={merchantId} initialData={health} />
        </div>
      )}

      {activeTab === 'journey' && (
        <div className="space-y-6">
          <MerchantJourneyTimeline merchantId={merchantId} />
        </div>
      )}

      {activeTab === 'profile' && (
        <div className="space-y-6">
          <MerchantProfileCard merchantId={merchantId} />
          <MerchantDetails merchantId={merchantId} />
          <MerchantFeatures merchantId={merchantId} />
        </div>
      )}

      {activeTab === 'activity' && (
        <div className="space-y-6">
          <MerchantCampaigns merchantId={merchantId} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <MerchantOrders merchantId={merchantId} />
            <MerchantShoppers merchantId={merchantId} />
          </div>
        </div>
      )}
    </div>
  );
}
