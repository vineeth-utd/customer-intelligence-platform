import type { ShopperBehaviorAnalyticsResult } from '../../types';

interface MerchantShopperBehaviorCardProps {
  behavior: ShopperBehaviorAnalyticsResult;
}

export function MerchantShopperBehaviorCard({ behavior }: MerchantShopperBehaviorCardProps) {
  const repeatRatePct = (behavior.repeat_purchase_rate * 100).toFixed(1);

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-base font-semibold text-gray-900">Shopper Behavior & Loyalty</h3>
        <p className="text-xs text-gray-500 mt-0.5">Customer retention and purchasing cohorts</p>
      </div>

      <div className="p-6 grid grid-cols-2 sm:grid-cols-3 gap-4">
        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="text-xs font-medium text-gray-500">Active Shoppers</div>
          <div className="text-xl font-bold text-gray-900 mt-1">
            {behavior.total_active_shoppers.toLocaleString()}
          </div>
          <div className="text-[11px] text-gray-500 mt-1">
            {behavior.new_shoppers} new • {behavior.returning_shoppers} returning
          </div>
        </div>

        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="text-xs font-medium text-gray-500">Purchasing Customers</div>
          <div className="text-xl font-bold text-gray-900 mt-1">
            {behavior.total_purchasing_shoppers.toLocaleString()}
          </div>
          <div className="text-[11px] text-gray-500 mt-1">
            {behavior.repeat_purchasing_shoppers} placed &gt; 1 order
          </div>
        </div>

        <div className="p-3 bg-gray-50 rounded-lg col-span-2 sm:col-span-1">
          <div className="text-xs font-medium text-gray-500">Repeat Purchase Rate</div>
          <div className="text-xl font-bold text-indigo-600 mt-1">{repeatRatePct}%</div>
          <div className="text-[11px] text-gray-500 mt-1">
            Cohort retention metric
          </div>
        </div>
      </div>
    </div>
  );
}

