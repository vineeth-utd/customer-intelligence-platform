import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { BaseChart } from '../../components/charts/BaseChart';
import type { CampaignAttributionResult } from '../../types';

interface CampaignAttributionCardProps {
  attribution: CampaignAttributionResult;
}

export function CampaignAttributionCard({ attribution }: CampaignAttributionCardProps) {
  const {
    direct_session,
    first_touch_journey,
    last_touch_journey,
    assisted_journey,
    explicit_recorded,
    direct_vs_cross_session_journeys,
  } = attribution;

  // Lenses for comparison
  const perspectives = useMemo(
    () => [
      {
        id: 'direct_session',
        name: 'Direct Session',
        subtitle: 'Same-session purchase',
        description:
          'Shopper clicked/opened campaign and completed order within the same session.',
        metric: direct_session,
        color: '#4f46e5',
      },
      {
        id: 'first_touch',
        name: 'First-Touch (Journey)',
        subtitle: 'Acquisition / Inception',
        description:
          'Credits campaign as the initial touchpoint that began the customer journey.',
        metric: first_touch_journey,
        color: '#0ea5e9',
      },
      {
        id: 'last_touch',
        name: 'Last-Touch (Journey)',
        subtitle: 'Closing / Conversion touch',
        description:
          'Credits campaign as the final campaign touchpoint before purchase.',
        metric: last_touch_journey,
        color: '#10b981',
      },
      {
        id: 'explicit_recorded',
        name: 'Explicit Recorded',
        subtitle: 'Operational tag observation',
        description:
          'Direct conversion logged with explicit campaign attribution tag.',
        metric: explicit_recorded,
        color: '#8b5cf6',
      },
    ],
    [direct_session, first_touch_journey, last_touch_journey, explicit_recorded]
  );

  // ECharts Bar Chart comparing perspectives
  const comparisonChartOption = useMemo<EChartsOption>(() => {
    const categories = perspectives.map((p) => p.name);
    const conversions = perspectives.map((p) => p.metric.conversions_count);
    const revenues = perspectives.map((p) => p.metric.attributed_revenue);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: unknown) => {
          if (!Array.isArray(params) || params.length === 0) return '';
          const p = params[0] as { dataIndex: number };
          const item = perspectives[p.dataIndex];
          if (!item) return '';
          return `<b>${item.name}</b><br/>` +
            `Conversions: <b>${item.metric.conversions_count.toLocaleString()}</b><br/>` +
            `Attributed Revenue: <b>$${item.metric.attributed_revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</b><br/>` +
            `Average Order Value: <b>$${item.metric.average_order_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</b>`;
        },
      },
      legend: {
        data: ['Conversions', 'Attributed Revenue ($)'],
        top: 0,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '14%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: {
          interval: 0,
          fontSize: 11,
        },
      },
      yAxis: [
        {
          type: 'value',
          name: 'Conversions',
          axisLabel: {
            formatter: (val: number) => val.toLocaleString(),
          },
        },
        {
          type: 'value',
          name: 'Revenue ($)',
          axisLabel: {
            formatter: (val: number) => `$${val.toLocaleString()}`,
          },
        },
      ],
      series: [
        {
          name: 'Conversions',
          type: 'bar',
          data: conversions,
          itemStyle: { color: '#4f46e5', borderRadius: [4, 4, 0, 0] },
          barMaxWidth: 36,
        },
        {
          name: 'Attributed Revenue ($)',
          type: 'bar',
          yAxisIndex: 1,
          data: revenues,
          itemStyle: { color: '#10b981', borderRadius: [4, 4, 0, 0] },
          barMaxWidth: 36,
        },
      ],
    };
  }, [perspectives]);

  // Donut chart for direct vs cross-session
  const directCount = direct_vs_cross_session_journeys?.direct_session || 0;
  const crossCount = direct_vs_cross_session_journeys?.cross_session || 0;
  const totalSessionJourneys = directCount + crossCount;

  const sessionChartOption = useMemo<EChartsOption>(() => {
    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: <b>{c}</b> ({d}%)',
      },
      legend: {
        bottom: '0%',
        left: 'center',
      },
      series: [
        {
          name: 'Conversion Velocity',
          type: 'pie',
          radius: ['45%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 6,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 12,
              fontWeight: 'bold',
            },
          },
          data: [
            {
              value: directCount,
              name: 'Same Session',
              itemStyle: { color: '#6366f1' },
            },
            {
              value: crossCount,
              name: 'Cross Session (Lagged)',
              itemStyle: { color: '#0ea5e9' },
            },
          ],
        },
      ],
    };
  }, [directCount, crossCount]);

  const hasAttributionData = perspectives.some(
    (p) => p.metric.conversions_count > 0 || p.metric.attributed_revenue > 0
  );

  return (
    <div className="space-y-6">
      {/* Notice Banner explaining alternative lenses */}
      <div className="bg-indigo-50/70 border-l-4 border-indigo-600 p-4 rounded-r-lg">
        <div className="flex items-start">
          <div className="flex-shrink-0 text-indigo-600">
            <svg className="w-5 h-5 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <div className="ml-3 text-xs text-indigo-900 leading-relaxed">
            <span className="font-bold">Alternative Attribution Perspectives:</span> Each model evaluates marketing impact through a distinct analytical lens. Because each model addresses a different attribution question (acquisition, closing, or immediacy), revenue and conversions are <strong>alternative views, not additive buckets</strong>. Figures must not be summed together.
            <div className="mt-1 font-medium text-indigo-700">
              Boundary Rule: Attribution is strictly restricted to completed orders within authoritative Shopper Journey boundaries.
            </div>
          </div>
        </div>
      </div>

      {/* Perspective Comparison Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {perspectives.map((p) => (
          <div
            key={p.id}
            className="bg-white p-5 rounded-lg shadow border border-gray-100 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-900">{p.name}</span>
                <span className="text-[10px] font-medium bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                  {p.subtitle}
                </span>
              </div>
              <p className="text-[11px] text-gray-500 mt-1 min-h-[32px]">{p.description}</p>
            </div>

            <div className="mt-4 pt-4 border-t border-gray-100 space-y-2">
              <div className="flex justify-between items-baseline">
                <span className="text-xs text-gray-500">Conversions</span>
                <span className="text-lg font-bold text-gray-900">
                  {p.metric.conversions_count.toLocaleString()}
                </span>
              </div>

              <div className="flex justify-between items-baseline">
                <span className="text-xs text-gray-500">Attributed Rev</span>
                <span className="text-base font-bold text-emerald-600">
                  {new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                  }).format(p.metric.attributed_revenue)}
                </span>
              </div>

              <div className="flex justify-between items-baseline">
                <span className="text-xs text-gray-500">Average Order Value</span>
                <span className="text-xs font-semibold text-gray-700">
                  {new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                  }).format(p.metric.average_order_value)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Perspective Chart & Assisted Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Comparative Bar Chart */}
        <div className="lg:col-span-2 bg-white p-6 rounded-lg shadow">
          <h4 className="text-sm font-semibold text-gray-900 mb-1">
            Attribution Comparison Across Analytical Lenses
          </h4>
          <p className="text-xs text-gray-500 mb-4">
            Side-by-side comparison of conversions and revenue under each model
          </p>
          {hasAttributionData ? (
            <BaseChart option={comparisonChartOption} height={290} />
          ) : (
            <div className="py-16 text-center text-gray-500 text-xs flex flex-col items-center justify-center">
              <svg className="w-10 h-10 text-gray-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <p className="font-medium text-gray-700">No Attributed Conversions in Selected Period</p>
              <p className="text-gray-400 mt-1 max-w-sm">
                No completed purchases intersected with active campaign touchpoints within the 7-day journey window for this date range.
              </p>
            </div>
          )}
        </div>

        {/* Dedicated Assisted Attribution Explainer */}
        <div className="bg-amber-50/50 border border-amber-200 rounded-lg p-6 shadow flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-bold text-amber-900 flex items-center gap-1.5">
                <span>Assisted Attribution</span>
              </h4>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-800 px-2 py-0.5 rounded">
                Non-Additive
              </span>
            </div>
            <p className="text-xs text-amber-800/90 mt-1">
              Multi-touch supporting influence across customer journeys
            </p>

            <div className="mt-5 space-y-3 bg-white/80 p-4 rounded-lg border border-amber-200/60">
              <div className="flex justify-between items-baseline">
                <span className="text-xs text-gray-600">Assisted Conversions</span>
                <span className="text-xl font-bold text-gray-900">
                  {assisted_journey.conversions_count.toLocaleString()}
                </span>
              </div>

              <div className="flex justify-between items-baseline">
                <span className="text-xs text-gray-600">Assisted Revenue</span>
                <span className="text-lg font-bold text-amber-700">
                  {new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                  }).format(assisted_journey.attributed_revenue)}
                </span>
              </div>

              <div className="flex justify-between items-baseline">
                <span className="text-xs text-gray-600">Assisted AOV</span>
                <span className="text-xs font-semibold text-gray-800">
                  {new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                  }).format(assisted_journey.average_order_value)}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 p-3 bg-amber-100/60 rounded text-[11px] text-amber-900 leading-snug">
            <strong>Important Attribution Boundary:</strong> Assisted attribution captures every journey where this campaign was touched prior to purchase. It is <em>non-exclusive</em> and overlaps with direct-session or first/last-touch credit. <strong>Do not sum assisted revenue with other models</strong> to prevent double-counting.
          </div>
        </div>
      </div>

      {/* Direct vs Cross-Session Influence */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h4 className="text-sm font-semibold text-gray-900 mb-1">
            Conversion Velocity: Same-Session vs Cross-Session
          </h4>
          <p className="text-xs text-gray-500 mb-4">
            Distinguishes immediate impulse purchases from delayed multi-session consideration cycles
          </p>

          {totalSessionJourneys > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
              <BaseChart option={sessionChartOption} height={200} />
              <div className="space-y-3 text-xs">
                <div className="p-3 bg-indigo-50/60 rounded-lg border border-indigo-100">
                  <span className="font-semibold text-indigo-900">Same Session:</span>
                  <div className="text-lg font-bold text-indigo-700">
                    {directCount.toLocaleString()}{' '}
                    <span className="text-xs font-normal text-indigo-600">
                      ({totalSessionJourneys > 0 ? ((directCount / totalSessionJourneys) * 100).toFixed(1) : 0}%)
                    </span>
                  </div>
                  <p className="text-[11px] text-indigo-800 mt-0.5">
                    Shopper converted in the exact session they clicked the campaign.
                  </p>
                </div>

                <div className="p-3 bg-sky-50/60 rounded-lg border border-sky-100">
                  <span className="font-semibold text-sky-900">Cross Session (Lagged):</span>
                  <div className="text-lg font-bold text-sky-700">
                    {crossCount.toLocaleString()}{' '}
                    <span className="text-xs font-normal text-sky-600">
                      ({totalSessionJourneys > 0 ? ((crossCount / totalSessionJourneys) * 100).toFixed(1) : 0}%)
                    </span>
                  </div>
                  <p className="text-[11px] text-sky-800 mt-0.5">
                    Shopper deliberated across subsequent sessions before purchasing.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-10 text-center text-gray-400 text-sm">
              No journey sessions recorded in this window.
            </div>
          )}
        </div>

        {/* Operational Observation Summary */}
        <div className="bg-white p-6 rounded-lg shadow flex flex-col justify-between">
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-1">
              Attribution Governance & Methodology
            </h4>
            <p className="text-xs text-gray-500 mb-4">
              Deterministic platform rules and boundary definitions
            </p>

            <ul className="space-y-2.5 text-xs text-gray-600">
              <li className="flex items-start gap-2">
                <span className="text-indigo-600 font-bold">•</span>
                <span>
                  <strong>Completed Orders Only:</strong> Orders cancelled, pending, or refunded are excluded from revenue credit.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-600 font-bold">•</span>
                <span>
                  <strong>Journey-Based Horizon:</strong> Multi-touch models respect the authoritative 7-day Shopper Journey window boundaries rather than unbounded historical lookbacks.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-600 font-bold">•</span>
                <span>
                  <strong>Explicit Recorded:</strong> Reflects client-side tracked conversions carrying the exact UTM/campaign identifier at order creation.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-600 font-bold">•</span>
                <span>
                  <strong>Deterministic Calculations:</strong> All metric values are computed by authoritative backend analytics services.
                </span>
              </li>
            </ul>
          </div>

          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
            <span>Model Scope: Completed Orders</span>
            <span className="font-mono text-[11px] bg-gray-100 px-2 py-0.5 rounded">Tenant Isolated</span>
          </div>
        </div>
      </div>
    </div>
  );
}
