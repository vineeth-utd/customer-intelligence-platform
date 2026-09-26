import { usePlatformSummary } from '../../hooks/queries';
import { KpiCard } from '../../components/common/KpiCard';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';

export function PlatformSummary() {
  const { data, isLoading, isError, refetch } = usePlatformSummary();

  if (isLoading) {
    return <LoadingSpinner message="Loading platform summary..." />;
  }

  if (isError || !data) {
    return <ErrorMessage message="Failed to load platform summary." retry={() => refetch()} />;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <KpiCard
        title="Active Merchants"
        value={data.active_merchants.toLocaleString()}
      />
      <KpiCard
        title="Total Revenue"
        value={new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(data.total_revenue)}
      />
      <KpiCard
        title="Total Orders"
        value={data.total_orders.toLocaleString()}
      />
      <KpiCard
        title="Active Shoppers"
        value={data.active_shoppers.toLocaleString()}
      />
    </div>
  );
}
