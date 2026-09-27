import { useMemo } from 'react';
import { MerchantDetails } from './MerchantDetails';
import { MerchantMetricsSummary } from './MerchantMetricsSummary';
import { MerchantMetricsTrend } from './MerchantMetricsTrend';
import { MerchantCampaigns } from './MerchantCampaigns';
import { MerchantShoppers } from './MerchantShoppers';
import { MerchantOrders } from './MerchantOrders';

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
      <MerchantCampaigns merchantId={merchantId} />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <MerchantOrders merchantId={merchantId} />
        <MerchantShoppers merchantId={merchantId} />
      </div>
    </div>
  );
}
