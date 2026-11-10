import { useShopperProfile } from '../../hooks/queries';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { KpiCard } from '../../components/common/KpiCard';

interface ShopperProfileCardProps {
  merchantId: string;
  shopperId: string;
}

export function ShopperProfileCard({ merchantId, shopperId }: ShopperProfileCardProps) {
  const { data: profile, isLoading, isError, refetch } = useShopperProfile(merchantId, shopperId);

  if (isLoading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow min-h-[220px] flex items-center justify-center">
        <LoadingSpinner message="Loading shopper profile intelligence..." />
      </div>
    );
  }

  if (isError || !profile) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <ErrorMessage message="Failed to load shopper profile." retry={() => refetch()} />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-medium text-gray-900">Calculated Shopper Profile</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Deterministic behavioral metrics and purchase intelligence
          </p>
        </div>
        <span className="text-[11px] text-gray-400">
          Generated: {new Date(profile.generated_at).toLocaleString()}
        </span>
      </div>

      <div className="p-6 space-y-6">
        {/* Core Financial & Order KPIs */}
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Spend & Order Metrics
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <KpiCard
              title="Total Spend"
              value={`$${profile.total_spend.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}`}
            />
            <KpiCard
              title="Total Orders"
              value={profile.total_orders.toLocaleString()}
            />
            <KpiCard
              title="Average Order Value"
              value={`$${profile.average_order_value.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}`}
            />
          </div>
        </div>

        {/* Engagement & Intent Signals */}
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Engagement & Behavioral Signals
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
              <span className="text-xs font-medium text-gray-500">Wishlist Items</span>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {profile.wishlist_item_count}
              </p>
              <span className="text-[11px] text-gray-400">Active saved wishlist items</span>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
              <span className="text-xs font-medium text-gray-500">Save for Later Items</span>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {profile.save_for_later_item_count}
              </p>
              <span className="text-[11px] text-gray-400">Saved items pending checkout</span>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
              <span className="text-xs font-medium text-gray-500">Campaign Engagements</span>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {profile.campaign_engagement_count}
              </p>
              <span className="text-[11px] text-gray-400">Direct marketing interactions</span>
            </div>
          </div>
        </div>

        {/* Preferences & Activity Recency */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-gray-100 text-sm">
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
            <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-3">
              Catalog Preferences
            </h5>
            <dl className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <dt className="text-gray-500 font-medium">Preferred Category:</dt>
                <dd className="text-gray-900 font-semibold mt-0.5">
                  {profile.preferred_category || 'No category preference detected'}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500 font-medium">Preferred Size:</dt>
                <dd className="text-gray-900 font-semibold mt-0.5">
                  {profile.preferred_size || 'No size recorded'}
                </dd>
              </div>
            </dl>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
            <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-3">
              Activity Recency
            </h5>
            <dl className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <dt className="text-gray-500 font-medium">Last Purchase:</dt>
                <dd className="text-gray-900 font-semibold mt-0.5">
                  {profile.last_purchase_at
                    ? new Date(profile.last_purchase_at).toLocaleDateString()
                    : 'No purchases recorded'}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500 font-medium">Last Storefront Activity:</dt>
                <dd className="text-gray-900 font-semibold mt-0.5">
                  {profile.last_activity_at
                    ? new Date(profile.last_activity_at).toLocaleString()
                    : 'No recent activity'}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
