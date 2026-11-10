import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { BaseChart } from '../../components/charts/BaseChart';
import type { CampaignJourneyCorrelationResult } from '../../types';

interface CampaignJourneyCorrelationCardProps {
  correlation: CampaignJourneyCorrelationResult;
}

export function CampaignJourneyCorrelationCard({
  correlation,
}: CampaignJourneyCorrelationCardProps) {
  const {
    total_journeys_touched,
    converted_journeys,
    non_converting_journeys,
    open_journeys,
    journey_conversion_rate,
    average_touch_to_conversion_seconds,
    drop_off_stages,
  } = correlation;

  const formatDuration = (seconds: number | null) => {
    if (seconds === null || seconds === undefined) return 'N/A';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
    return `${(seconds / 86400).toFixed(1)}d`;
  };

  // Drop-off stages chart
  const dropOffChartOption = useMemo<EChartsOption>(() => {
    const entries = Object.entries(drop_off_stages || {});
    if (entries.length === 0) return {};

    // Sort descending by count
    entries.sort((a, b) => b[1] - a[1]);
    const stages = entries.map(([stage]) => stage.replace(/_/g, ' '));
    const counts = entries.map(([, count]) => count);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: unknown) => {
          if (!Array.isArray(params) || params.length === 0) return '';
          const p = params[0] as { dataIndex: number };
          const stageName = stages[p.dataIndex];
          const count = counts[p.dataIndex];
          return `<b>${stageName}</b><br/>Drop-offs: <b>${count.toLocaleString()}</b>`;
        },
      },
      grid: {
        left: '4%',
        right: '4%',
        top: '6%',
        bottom: '8%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        name: 'Drop-off Count',
        axisLabel: {
          formatter: (val: number) => val.toLocaleString(),
        },
      },
      yAxis: {
        type: 'category',
        data: stages,
        inverse: true,
        axisTick: { alignWithLabel: true },
      },
      series: [
        {
          name: 'Drop-offs',
          type: 'bar',
          data: counts,
          itemStyle: {
            color: '#ef4444',
            borderRadius: [0, 4, 4, 0],
          },
          barMaxWidth: 28,
          label: {
            show: true,
            position: 'right',
            formatter: (p: { value: unknown }) => Number(p.value).toLocaleString(),
          },
        },
      ],
    };
  }, [drop_off_stages]);

  const hasDropOffs =
    Boolean(drop_off_stages) && Object.values(drop_off_stages || {}).some((v) => v > 0);

  return (
    <div className="space-y-6">
      {/* Outcome Distribution KPI Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-lg shadow border border-gray-100">
          <div className="text-xs font-medium text-gray-500">Journeys Touched</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {total_journeys_touched.toLocaleString()}
          </div>
          <div className="text-[11px] text-gray-400 mt-1">Total customer journeys</div>
        </div>

        <div className="bg-emerald-50/70 p-4 rounded-lg shadow border border-emerald-200">
          <div className="text-xs font-semibold text-emerald-800">Converted</div>
          <div className="text-2xl font-bold text-emerald-900 mt-1">
            {converted_journeys.toLocaleString()}
          </div>
          <div className="text-[11px] text-emerald-700 mt-1">
            {total_journeys_touched > 0
              ? `${((converted_journeys / total_journeys_touched) * 100).toFixed(1)}% of touched`
              : '0%'}
          </div>
        </div>

        <div className="bg-slate-50 p-4 rounded-lg shadow border border-slate-200">
          <div className="text-xs font-semibold text-slate-700">Non-Converting</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">
            {non_converting_journeys.toLocaleString()}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Closed without order</div>
        </div>

        <div className="bg-blue-50/70 p-4 rounded-lg shadow border border-blue-200">
          <div className="text-xs font-semibold text-blue-800">Open / Active</div>
          <div className="text-2xl font-bold text-blue-900 mt-1">
            {open_journeys.toLocaleString()}
          </div>
          <div className="text-[11px] text-blue-700 mt-1">Active within 7-day window</div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border border-gray-100">
          <div className="text-xs font-medium text-gray-500">Conversion Rate</div>
          <div className="text-2xl font-bold text-indigo-600 mt-1">
            {(journey_conversion_rate * 100).toFixed(1)}%
          </div>
          <div className="text-[11px] text-gray-400 mt-1">Touch-to-order rate</div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border border-gray-100">
          <div className="text-xs font-medium text-gray-500">Avg Touch-to-Order</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {formatDuration(average_touch_to_conversion_seconds)}
          </div>
          <div className="text-[11px] text-gray-400 mt-1">Latency to conversion</div>
        </div>
      </div>

      {/* Drop-Off Stages Chart & Journey Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white p-6 rounded-lg shadow">
          <h4 className="text-sm font-semibold text-gray-900 mb-1">
            Journey Drop-Off Stages
          </h4>
          <p className="text-xs text-gray-500 mb-4">
            Terminal events for shopper journeys that interacted with this campaign but ended without a completed purchase
          </p>

          {hasDropOffs ? (
            <BaseChart option={dropOffChartOption} height={280} />
          ) : (
            <div className="py-12 text-center text-gray-400 text-sm">
              No journey drop-offs recorded for this campaign in the selected period.
            </div>
          )}
        </div>

        <div className="bg-white p-6 rounded-lg shadow flex flex-col justify-between">
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-1">
              Shopper Journey Context
            </h4>
            <p className="text-xs text-gray-500 mb-4">
              Understanding multi-session customer impact
            </p>

            <div className="space-y-3 text-xs text-gray-600">
              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="font-semibold text-gray-900">Deterministic 7-Day Window Boundary:</span>
                <p className="mt-1 text-gray-500 text-[11px] leading-relaxed">
                  Shopper Journeys connect multi-session customer touchpoints across storefront and marketing interactions for up to 7 days from initial session. Completed orders close the journey as Converted; reaching the 7-day boundary without conversion marks it Non-Converting.
                </p>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="font-semibold text-gray-900">Touch-to-Order Latency:</span>
                <p className="mt-1 text-gray-500 text-[11px]">
                  Measures the exact elapsed time between the shopper&apos;s first interaction with this campaign and their eventual purchase completion.
                </p>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="font-semibold text-gray-900">Drop-Off Diagnosis:</span>
                <p className="mt-1 text-gray-500 text-[11px]">
                  Identifies friction points (e.g. cart abandonment vs bounce after product search) for campaign-engaged traffic.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

