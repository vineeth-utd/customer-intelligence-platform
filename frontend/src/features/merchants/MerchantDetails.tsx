import { useMerchant } from '../../hooks/queries';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';

export function MerchantDetails({ merchantId }: { merchantId: string }) {
  const { data, isLoading, isError, refetch } = useMerchant(merchantId);

  if (isLoading) {
    return <div className="bg-white p-6 rounded-lg shadow mb-8"><LoadingSpinner message="Loading merchant details..." /></div>;
  }

  if (isError || !data) {
    return <div className="bg-white p-6 rounded-lg shadow mb-8"><ErrorMessage message="Failed to load merchant details." retry={() => refetch()} /></div>;
  }

  return (
    <div className="bg-white rounded-lg shadow mb-8 overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-200">
        <h3 className="text-lg leading-6 font-medium text-gray-900">Merchant Details</h3>
        <p className="mt-1 max-w-2xl text-sm text-gray-500">Details and active subscription for {data.merchant_name}.</p>
      </div>
      <div className="px-6 py-5 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-gray-500">Store ID</dt>
              <dd className="mt-1 text-sm text-gray-900">{data.shopify_store_id}</dd>
            </div>
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-gray-500">Email</dt>
              <dd className="mt-1 text-sm text-gray-900">{data.email}</dd>
            </div>
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-gray-500">Status</dt>
              <dd className="mt-1 text-sm text-gray-900 capitalize">{data.app_install_status.replace('_', ' ')}</dd>
            </div>
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-gray-500">Currency</dt>
              <dd className="mt-1 text-sm text-gray-900">{data.store_currency}</dd>
            </div>
          </dl>
        </div>
        <div>
          <h4 className="text-md font-medium text-gray-900 mb-4">Subscription Information</h4>
          {data.active_subscription ? (
            <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Plan</dt>
                <dd className="mt-1 text-sm text-gray-900 font-medium">{data.active_subscription.plan_name}</dd>
              </div>
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Status</dt>
                <dd className="mt-1 text-sm text-gray-900 capitalize">{data.active_subscription.status}</dd>
              </div>
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Billing Cycle</dt>
                <dd className="mt-1 text-sm text-gray-900 capitalize">{data.active_subscription.billing_cycle}</dd>
              </div>
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Started At</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {new Date(data.active_subscription.started_at).toLocaleDateString()}
                </dd>
              </div>
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Amount Paid</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  ${data.active_subscription.amount_paid.toFixed(2)}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-gray-500">No active subscription found.</p>
          )}
        </div>
      </div>
    </div>
  );
}
