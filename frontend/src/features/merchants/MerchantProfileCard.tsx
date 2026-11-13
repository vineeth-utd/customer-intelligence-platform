import { useMerchantProfile, useMerchant } from '../../hooks/queries';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { formatCurrency } from '../../utils';

interface MerchantProfileCardProps {
  merchantId: string;
  currency?: string;
}

export function MerchantProfileCard({ merchantId, currency }: MerchantProfileCardProps) {
  const { data, isLoading, isError, refetch } = useMerchantProfile(merchantId);
  const { data: merchant } = useMerchant(merchantId);

  const effectiveCurrency = currency || merchant?.store_currency || 'USD';

  if (isLoading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <LoadingSpinner message="Loading merchant profile..." />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <ErrorMessage message="Failed to load merchant profile." retry={() => refetch()} />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-medium text-gray-900">Deterministic Merchant Profile</h3>
          <p className="text-xs text-gray-500 mt-0.5">Authoritative business profile data product</p>
        </div>
        <span className="text-xs text-gray-400">
          Updated {new Date(data.generated_at).toLocaleString()}
        </span>
      </div>

      <div className="p-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
        <div>
          <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Total Revenue</dt>
          <dd className="mt-1 text-2xl font-bold text-gray-900">
            {formatCurrency(data.total_revenue, effectiveCurrency)}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Total Orders</dt>
          <dd className="mt-1 text-2xl font-bold text-gray-900">{data.total_orders.toLocaleString()}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Average Order Value</dt>
          <dd className="mt-1 text-2xl font-bold text-gray-900">
            {formatCurrency(data.average_order_value, effectiveCurrency)}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Store Conversion Rate</dt>
          <dd className="mt-1 text-2xl font-bold text-gray-900">
            {(data.conversion_rate * 100).toFixed(2)}%
          </dd>
        </div>

        <div>
          <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Total Shoppers</dt>
          <dd className="mt-1 text-lg font-semibold text-gray-900">{data.total_shoppers.toLocaleString()}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Catalog Products</dt>
          <dd className="mt-1 text-lg font-semibold text-gray-900">{data.total_products.toLocaleString()}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Active Campaigns</dt>
          <dd className="mt-1 text-lg font-semibold text-gray-900">{data.active_campaign_count} / {data.total_campaigns}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Enabled Features</dt>
          <dd className="mt-1 text-lg font-semibold text-gray-900">{data.enabled_feature_count}</dd>
        </div>
      </div>
    </div>
  );
}
