import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { BaseChart } from './BaseChart';
import type { ConversionFunnelStage } from '../../types';

interface FunnelChartProps {
  stages: ConversionFunnelStage[];
}

export function FunnelChart({ stages }: FunnelChartProps) {
  const chartOption = useMemo<EChartsOption>(() => {
    if (!stages || stages.length === 0) return {};

    const stageNames = stages.map((s) => s.stage_name.replace(/_/g, ' '));
    const counts = stages.map((s) => s.count);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: unknown) => {
          if (!Array.isArray(params) || params.length === 0) return '';
          const p = params[0] as { dataIndex: number };
          const stage = stages[p.dataIndex];
          if (!stage) return '';
          const dropOff = stage.drop_off_count
            ? `<br/><span style="color:#ef4444">Drop-off: ${stage.drop_off_count.toLocaleString()} (${(stage.drop_off_rate * 100).toFixed(1)}%)</span>`
            : '';
          const stepRate = stage.step_conversion_rate !== null
            ? `<br/>Step Conversion: ${(stage.step_conversion_rate * 100).toFixed(1)}%`
            : '';
          const overallRate = stage.overall_conversion_rate !== null && stage.overall_conversion_rate !== undefined
            ? `<br/>Overall Rate: ${(stage.overall_conversion_rate * 100).toFixed(1)}%`
            : '';
          return `<b>${stage.stage_name.replace(/_/g, ' ')}</b><br/>Volume: ${stage.count.toLocaleString()}${stepRate}${overallRate}${dropOff}`;
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
        axisLabel: {
          formatter: (val: number) => val.toLocaleString(),
        },
      },
      yAxis: {
        type: 'category',
        data: stageNames,
        axisTick: { alignWithLabel: true },
        inverse: true,
      },
      series: [
        {
          name: 'Sessions',
          type: 'bar',
          data: counts,
          itemStyle: {
            color: '#4f46e5',
            borderRadius: [0, 4, 4, 0],
          },
          label: {
            show: true,
            position: 'right',
            formatter: (p: { value: unknown }) => Number(p.value).toLocaleString(),
          },
        },
      ],
    };
  }, [stages]);

  if (!stages || stages.length === 0) {
    return <p className="text-gray-500 text-sm text-center py-6">No funnel stages recorded.</p>;
  }

  return <BaseChart option={chartOption} height={260} />;
}

