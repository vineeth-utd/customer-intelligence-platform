import { useMerchantMetricsSummary, useMerchant } from '../../hooks/queries';
import { KpiCard } from '../../components/common/KpiCard';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { formatCurrency } from '../../utils';

interface MerchantMetricsSummaryProps {
  merchantId: string;
  startDate: string;
  endDate: string;
  currency?: string;
}

export function MerchantMetricsSummary({
  merchantId,
  startDate,
  endDate,
  currency,
}: MerchantMetricsSummaryProps) {
  const { data, isLoading, isError, refetch } = useMerchantMetricsSummary(merchantId, startDate, endDate);
  const { data: merchant } = useMerchant(merchantId);

  const effectiveCurrency = currency || merchant?.store_currency || 'USD';

  if (isLoading) {
    return <LoadingSpinner message="Loading merchant metrics..." />;
  }

  if (isError || !data) {
    return <ErrorMessage message="Failed to load merchant metrics." retry={() => refetch()} />;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <KpiCard
        title="Revenue"
        value={formatCurrency(data.revenue, effectiveCurrency)}
      />
      <KpiCard
        title="Orders"
        value={data.order_count.toLocaleString()}
      />
      <KpiCard
        title="Unique Shoppers"
        value={data.unique_shoppers.toLocaleString()}
      />
      <KpiCard
        title="Conversion Rate"
        value={`${(data.conversion_rate * 100).toFixed(2)}%`}
      />
    </div>
  );
}
