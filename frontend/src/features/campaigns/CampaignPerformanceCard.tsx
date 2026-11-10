import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { BaseChart } from '../../components/charts/BaseChart';
import { KpiCard } from '../../components/common/KpiCard';
import type { CampaignPerformanceDetailResult } from '../../types';

interface CampaignPerformanceCardProps {
  performance: CampaignPerformanceDetailResult;
}

export function CampaignPerformanceCard({ performance }: CampaignPerformanceCardProps) {
  const {
    delivered_count,
    opened_count,
    clicked_count,
    open_rate,
    click_through_rate,
    trends,
    delivered_growth_pct,
    opened_growth_pct,
    clicked_growth_pct,
    prior_period_delivered,
    prior_period_opened,
    prior_period_clicked,
  } = performance;

  // Trend line chart
  const trendChartOption = useMemo<EChartsOption>(() => {
    if (!trends || trends.length === 0) return {};

    const dates = trends.map((t) => t.metric_date);
    const delivered = trends.map((t) => t.delivered_count);
    const opened = trends.map((t) => t.opened_count);
    const clicked = trends.map((t) => t.clicked_count);
    const converted = trends.map((t) => t.converted_count);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      legend: {
        data: ['Delivered', 'Opened', 'Clicked', 'Converted'],
        top: 0,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '12%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
      },
      yAxis: {
        type: 'value',
        name: 'Events',
        axisLabel: {
          formatter: (val: number) => val.toLocaleString(),
        },
      },
      series: [
        {
          name: 'Delivered',
          type: 'line',
          smooth: true,
          data: delivered,
          itemStyle: { color: '#6366f1' },
          areaStyle: { color: 'rgba(99, 102, 241, 0.08)' },
        },
        {
          name: 'Opened',
          type: 'line',
          smooth: true,
          data: opened,
          itemStyle: { color: '#0ea5e9' },
        },
        {
          name: 'Clicked',
          type: 'line',
          smooth: true,
          data: clicked,
          itemStyle: { color: '#f59e0b' },
        },
        {
          name: 'Converted',
          type: 'line',
          smooth: true,
          data: converted,
          itemStyle: { color: '#10b981' },
        },
      ],
    };
  }, [trends]);

  // Progression calculation
  const openPct = delivered_count > 0 ? (opened_count / delivered_count) * 100 : 0;
  const clickPct = delivered_count > 0 ? (clicked_count / delivered_count) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Top Engagement KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard
          title="Delivered"
          value={delivered_count.toLocaleString()}
          trend={
            delivered_growth_pct !== null && delivered_growth_pct !== undefined
              ? {
                  value: `${delivered_growth_pct >= 0 ? '+' : ''}${(delivered_growth_pct * 100).toFixed(1)}%`,
                  isPositive: delivered_growth_pct >= 0,
                }
              : undefined
          }
        />
        <KpiCard
          title="Opened"
          value={opened_count.toLocaleString()}
          trend={
            opened_growth_pct !== null && opened_growth_pct !== undefined
              ? {
                  value: `${opened_growth_pct >= 0 ? '+' : ''}${(opened_growth_pct * 100).toFixed(1)}%`,
                  isPositive: opened_growth_pct >= 0,
                }
              : undefined
          }
        />
        <KpiCard
          title="Clicked"
          value={clicked_count.toLocaleString()}
          trend={
            clicked_growth_pct !== null && clicked_growth_pct !== undefined
              ? {
                  value: `${clicked_growth_pct >= 0 ? '+' : ''}${(clicked_growth_pct * 100).toFixed(1)}%`,
                  isPositive: clicked_growth_pct >= 0,
                }
              : undefined
          }
        />
        <KpiCard
          title="Open Rate"
          value={`${(open_rate * 100).toFixed(1)}%`}
        />
        <KpiCard
          title="Click-Through Rate"
          value={`${(click_through_rate * 100).toFixed(1)}%`}
        />
      </div>

      {/* Engagement Progression & Period Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Progression visual */}
        <div className="lg:col-span-2 bg-white p-6 rounded-lg shadow">
          <h4 className="text-sm font-semibold text-gray-900 mb-1">
            Delivery to Click Progression
          </h4>
          <p className="text-xs text-gray-500 mb-6">
            Audience funnel from dispatch to active engagement
          </p>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs font-medium text-gray-700 mb-1">
                <span>1. Delivered</span>
                <span>{delivered_count.toLocaleString()} recipients (100%)</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                <div className="bg-indigo-600 h-full rounded-full" style={{ width: '100%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-gray-700 mb-1">
                <span>2. Opened</span>
                <span>
                  {opened_count.toLocaleString()} recipients (
                  {(open_rate * 100).toFixed(1)}% open rate)
                </span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-sky-500 h-full rounded-full transition-all"
                  style={{ width: `${Math.min(100, Math.max(0, openPct))}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-gray-700 mb-1">
                <span>3. Clicked</span>
                <span>
                  {clicked_count.toLocaleString()} recipients (
                  {(click_through_rate * 100).toFixed(1)}% CTR)
                </span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-amber-500 h-full rounded-full transition-all"
                  style={{ width: `${Math.min(100, Math.max(0, clickPct))}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Prior period comparison summary */}
        <div className="bg-white p-6 rounded-lg shadow flex flex-col justify-between">
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-1">
              Prior Period Trajectory
            </h4>
            <p className="text-xs text-gray-500 mb-4">
              Comparison against previous window of equal length
            </p>

            <div className="space-y-3">
              <div className="p-3 bg-gray-50 rounded-lg flex items-center justify-between">
                <div>
                  <div className="text-xs text-gray-500">Prior Delivered</div>
                  <div className="text-sm font-semibold text-gray-900">
                    {prior_period_delivered.toLocaleString()}
                  </div>
                </div>
                <span
                  className={`text-xs font-bold ${
                    (delivered_growth_pct ?? 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'
                  }`}
                >
                  {delivered_growth_pct !== null && delivered_growth_pct !== undefined
                    ? `${delivered_growth_pct >= 0 ? '+' : ''}${(delivered_growth_pct * 100).toFixed(1)}%`
                    : 'N/A'}
                </span>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg flex items-center justify-between">
                <div>
                  <div className="text-xs text-gray-500">Prior Opened</div>
                  <div className="text-sm font-semibold text-gray-900">
                    {prior_period_opened.toLocaleString()}
                  </div>
                </div>
                <span
                  className={`text-xs font-bold ${
                    (opened_growth_pct ?? 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'
                  }`}
                >
                  {opened_growth_pct !== null && opened_growth_pct !== undefined
                    ? `${opened_growth_pct >= 0 ? '+' : ''}${(opened_growth_pct * 100).toFixed(1)}%`
                    : 'N/A'}
                </span>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg flex items-center justify-between">
                <div>
                  <div className="text-xs text-gray-500">Prior Clicked</div>
                  <div className="text-sm font-semibold text-gray-900">
                    {prior_period_clicked.toLocaleString()}
                  </div>
                </div>
                <span
                  className={`text-xs font-bold ${
                    (clicked_growth_pct ?? 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'
                  }`}
                >
                  {clicked_growth_pct !== null && clicked_growth_pct !== undefined
                    ? `${clicked_growth_pct >= 0 ? '+' : ''}${(clicked_growth_pct * 100).toFixed(1)}%`
                    : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Daily Performance Trend Chart */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h4 className="text-sm font-semibold text-gray-900 mb-1">
          Daily Performance & Engagement Trends
        </h4>
        <p className="text-xs text-gray-500 mb-4">
          Volume of dispatches, opens, clicks, and conversions across the selected date range
        </p>

        {trends && trends.length > 0 ? (
          <BaseChart option={trendChartOption} height={320} />
        ) : (
          <div className="py-12 text-center text-gray-400 text-sm">
            No daily trend points recorded in the selected date range.
          </div>
        )}
      </div>
    </div>
  );
}

