import { useMemo } from 'react';
import { MerchantDetails } from './MerchantDetails';
import { MerchantMetricsSummary } from './MerchantMetricsSummary';
import { MerchantMetricsTrend } from './MerchantMetricsTrend';

export function MerchantOverview({ merchantId }: { merchantId: string }) {
  const { startDate, endDate } = useMemo(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    return {
      startDate: start.toISOString().split('T')[0],
      endDate: end.toISOString().split('T')[0]
    };
  }, []);

  return (
    <div>
      <MerchantDetails merchantId={merchantId} />
      <MerchantMetricsSummary merchantId={merchantId} startDate={startDate} endDate={endDate} />
      <MerchantMetricsTrend merchantId={merchantId} startDate={startDate} endDate={endDate} />
    </div>
  );
}
