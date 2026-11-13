import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { useMerchantMetricsTrend } from '../../hooks/queries';
import { BaseChart } from '../../components/charts/BaseChart';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { formatCurrency, getCurrencySymbol } from '../../utils';

interface MerchantMetricsTrendProps {
  merchantId: string;
  startDate: string;
  endDate: string;
  currency?: string;
}

export function MerchantMetricsTrend({
  merchantId,
  startDate,
  endDate,
  currency = 'USD',
}: MerchantMetricsTrendProps) {
  const { data, isLoading, isError, refetch } = useMerchantMetricsTrend(merchantId, startDate, endDate);

  const currencySymbol = getCurrencySymbol(currency);

  const chartOption = useMemo<EChartsOption>(() => {
    if (!data) return {};

    const dates = data.map((d) => d.metric_date);
    const revenue = data.map((d) => d.revenue);
    const orders = data.map((d) => d.order_count);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params: unknown) => {
          if (!Array.isArray(params) || params.length === 0) return '';
          let result = `<b>${(params[0] as { axisValueLabel: string }).axisValueLabel}</b>`;
          params.forEach((item: { seriesName: string; value: number; color: string }) => {
            const valStr =
              item.seriesName === 'Revenue'
                ? formatCurrency(item.value, currency)
                : Number(item.value).toLocaleString();
            result += `<br/><span style="color:${item.color}">●</span> ${item.seriesName}: <b>${valStr}</b>`;
          });
          return result;
        },
      },
      legend: {
        data: ['Revenue', 'Orders'],
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
      },
      yAxis: [
        {
          type: 'value',
          name: `Revenue (${currencySymbol})`,
          axisLabel: {
            formatter: (val: number) => `${currencySymbol}${val.toLocaleString()}`,
          },
        },
        {
          type: 'value',
          name: 'Orders',
          alignTicks: true,
          axisLabel: {
            formatter: '{value}',
          },
        },
      ],
      series: [
        {
          name: 'Revenue',
          type: 'line',
          smooth: true,
          data: revenue,
          itemStyle: {
            color: '#4f46e5',
          },
        },
        {
          name: 'Orders',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          data: orders,
          itemStyle: {
            color: '#10b981',
          },
        },
      ],
    };
  }, [data, currency, currencySymbol]);

  if (isLoading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <LoadingSpinner message="Loading metric trends..." />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <ErrorMessage message="Failed to load metric trends." retry={() => refetch()} />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-base font-semibold text-gray-900">Performance Over Time</h3>
        <p className="text-xs text-gray-500 mt-0.5">Daily revenue and order volume trends</p>
      </div>
      <div className="p-6">
        <BaseChart option={chartOption} height={300} />
      </div>
    </div>
  );
}
