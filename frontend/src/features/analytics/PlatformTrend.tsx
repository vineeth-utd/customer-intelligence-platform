import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { usePlatformTrend } from '../../hooks/queries';
import { BaseChart } from '../../components/charts/BaseChart';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';

export function PlatformTrend({ startDate, endDate }: { startDate: string; endDate: string }) {
  const { data, isLoading, isError, refetch } = usePlatformTrend(startDate, endDate);

  const chartOption = useMemo<EChartsOption>(() => {
    if (!data) return {};

    const dates = data.map(d => d.metric_date);
    const revenue = data.map(d => d.total_revenue);
    const orders = data.map(d => d.total_orders);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: ['Revenue', 'Orders']
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates
      },
      yAxis: [
        {
          type: 'value',
          name: 'Revenue',
          axisLabel: {
            formatter: '${value}'
          }
        },
        {
          type: 'value',
          name: 'Orders',
          alignTicks: true,
          axisLabel: {
            formatter: '{value}'
          }
        }
      ],
      series: [
        {
          name: 'Revenue',
          type: 'line',
          smooth: true,
          data: revenue,
          yAxisIndex: 0,
          itemStyle: { color: '#4f46e5' },
          areaStyle: {
            color: 'rgba(79, 70, 229, 0.1)'
          }
        },
        {
          name: 'Orders',
          type: 'line',
          smooth: true,
          data: orders,
          yAxisIndex: 1,
          itemStyle: { color: '#0ea5e9' }
        }
      ]
    };
  }, [data]);

  if (isLoading) {
    return <div className="bg-white p-6 rounded-lg shadow"><LoadingSpinner message="Loading trends..." /></div>;
  }

  if (isError || !data) {
    return <div className="bg-white p-6 rounded-lg shadow"><ErrorMessage message="Failed to load trends." retry={() => refetch()} /></div>;
  }

  if (data.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow flex flex-col items-center justify-center min-h-[400px]">
        <p className="text-gray-500">No trend data available for this period.</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow mb-8">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Platform Growth Trend</h3>
      <BaseChart option={chartOption} />
    </div>
  );
}
