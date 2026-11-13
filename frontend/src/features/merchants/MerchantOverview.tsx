import { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useMerchantDashboard } from '../../hooks/queries';
import { DateRangePicker } from '../../components/common/DateRangePicker';
import { StatusBadge } from '../../components/common/StatusBadge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { KpiCard } from '../../components/common/KpiCard';
import { formatCurrency, formatGrowthRate, formatPercent, parseNumericValue } from '../../utils';

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

type TabKey =
  | 'overview'
  | 'shoppers'
  | 'campaigns'
  | 'health'
  | 'journey'
  | 'profile'
  | 'activity';

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
  const [searchParams, setSearchParams] = useSearchParams();
  const validTabs: TabKey[] = [
    'overview',
    'shoppers',
    'campaigns',
    'health',
    'journey',
    'profile',
    'activity',
  ];
  const tabParam = searchParams.get('tab') as TabKey | null;
  const activeTab = tabParam && validTabs.includes(tabParam) ? tabParam : 'overview';

  const handleTabChange = (key: TabKey) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (key === 'overview') {
          next.delete('tab');
        } else {
          next.set('tab', key);
        }
        return next;
      },
      { replace: true }
    );
  };

  const navRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = useCallback(() => {
    const el = navRef.current;
    if (!el) return;
    const { scrollLeft, scrollWidth, clientWidth } = el;
    setCanScrollLeft(scrollLeft > 4);
    setCanScrollRight(scrollLeft + clientWidth < scrollWidth - 4);
  }, []);

  useEffect(() => {
    const el = navRef.current;
    if (!el) return;
    checkScroll();
    el.addEventListener('scroll', checkScroll, { passive: true });
    window.addEventListener('resize', checkScroll);
    return () => {
      el.removeEventListener('scroll', checkScroll);
      window.removeEventListener('resize', checkScroll);
    };
  }, [checkScroll]);

  useEffect(() => {
    const el = navRef.current;
    if (!el) return;
    const activeBtn = el.querySelector<HTMLElement>('[data-active="true"]');
    if (activeBtn) {
      activeBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
    }
    checkScroll();
  }, [activeTab, checkScroll]);

  const scrollNav = (delta: number) => {
    navRef.current?.scrollBy({ left: delta, behavior: 'smooth' });
  };

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
    { key: 'shoppers', label: 'Shoppers & Customers' },
    { key: 'campaigns', label: 'Campaigns & Marketing' },
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
      <div className="relative border-b border-gray-200 bg-white px-2 sm:px-4 rounded-t-lg shadow-xs">
        {canScrollLeft && (
          <button
            type="button"
            onClick={() => scrollNav(-200)}
            aria-label="Scroll tabs left"
            className="absolute left-0 top-0 bottom-0 z-10 px-2 bg-gradient-to-r from-white via-white/95 to-transparent flex items-center justify-center text-gray-500 hover:text-indigo-600 transition-colors"
          >
            <span className="w-6 h-6 rounded-full bg-white border border-gray-200 flex items-center justify-center shadow-xs text-xs font-bold">
              ‹
            </span>
          </button>
        )}

        <nav
          ref={navRef}
          className="-mb-px flex space-x-6 overflow-x-auto scroll-smooth py-0.5"
          aria-label="Tabs"
        >
          {tabs.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                data-active={isActive ? 'true' : 'false'}
                onClick={() => handleTabChange(tab.key)}
                className={`whitespace-nowrap shrink-0 py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors focus:outline-none focus:ring-1 focus:ring-indigo-500 rounded-t ${isActive
                  ? 'border-indigo-600 text-indigo-600 font-semibold'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
              >
                <span>{tab.label}</span>
                {tab.badge && (
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${tab.badge === 'HEALTHY'
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

        {canScrollRight && (
          <button
            type="button"
            onClick={() => scrollNav(200)}
            aria-label="Scroll tabs right"
            className="absolute right-0 top-0 bottom-0 z-10 px-2 bg-gradient-to-l from-white via-white/95 to-transparent flex items-center justify-center text-gray-500 hover:text-indigo-600 transition-colors"
          >
            <span className="w-6 h-6 rounded-full bg-white border border-gray-200 flex items-center justify-center shadow-xs text-xs font-bold">
              ›
            </span>
          </button>
        )}
      </div>

      {/* Tab Contents */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <KpiCard
              title="Revenue"
              value={formatCurrency(revenue.total_revenue, merchant.store_currency)}
              trend={
                parseNumericValue(revenue.prior_period_comparison?.revenue_growth_pct) !== null
                  ? {
                    value: formatGrowthRate(revenue.prior_period_comparison?.revenue_growth_pct),
                    isPositive: (parseNumericValue(revenue.prior_period_comparison?.revenue_growth_pct) ?? 0) >= 0,
                  }
                  : undefined
              }
            />
            <KpiCard
              title="Total Orders"
              value={revenue.total_orders.toLocaleString()}
              trend={
                parseNumericValue(revenue.prior_period_comparison?.order_growth_pct) !== null
                  ? {
                    value: formatGrowthRate(revenue.prior_period_comparison?.order_growth_pct),
                    isPositive: (parseNumericValue(revenue.prior_period_comparison?.order_growth_pct) ?? 0) >= 0,
                  }
                  : undefined
              }
            />
            <KpiCard
              title="Average Order Value"
              value={formatCurrency(revenue.average_order_value, merchant.store_currency)}
              trend={
                parseNumericValue(revenue.prior_period_comparison?.aov_growth_pct) !== null
                  ? {
                    value: formatGrowthRate(revenue.prior_period_comparison?.aov_growth_pct),
                    isPositive: (parseNumericValue(revenue.prior_period_comparison?.aov_growth_pct) ?? 0) >= 0,
                  }
                  : undefined
              }
            />
            <KpiCard
              title="Conversion Rate"
              value={formatPercent(summary.conversion_rate, 2)}
            />
          </div>

          {/* Revenue & Funnel Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <MerchantRevenueCard revenue={revenue} currency={merchant.store_currency} />
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
            currency={merchant.store_currency}
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
          <MerchantProfileCard merchantId={merchantId} currency={merchant.store_currency} />
          <MerchantDetails merchantId={merchantId} />
          <MerchantFeatures merchantId={merchantId} />
        </div>
      )}

      {activeTab === 'shoppers' && (
        <div className="space-y-6">
          <MerchantShoppers merchantId={merchantId} />
        </div>
      )}

      {activeTab === 'campaigns' && (
        <div className="space-y-6">
          <MerchantCampaigns merchantId={merchantId} currency={merchant.store_currency} />
        </div>
      )}

      {activeTab === 'activity' && (
        <div className="space-y-6">
          <MerchantOrders merchantId={merchantId} />
        </div>
      )}
    </div>
  );
}
