import type { RevenueAnalyticsResult } from '../../types';
import { formatCurrency, formatGrowthRate, parseNumericValue } from '../../utils';

interface MerchantRevenueCardProps {
  revenue: RevenueAnalyticsResult;
  currency?: string;
}

export function MerchantRevenueCard({ revenue, currency = 'USD' }: MerchantRevenueCardProps) {
  const { prior_period_comparison, customer_revenue_breakdown } = revenue;

  const totalRev = parseNumericValue(revenue.total_revenue) ?? 0;
  const newRev = parseNumericValue(customer_revenue_breakdown?.new_customer_revenue) ?? 0;
  const repeatRev = parseNumericValue(customer_revenue_breakdown?.repeat_customer_revenue) ?? 0;

  const newPct = totalRev > 0 ? ((newRev / totalRev) * 100).toFixed(1) : '0';
  const repeatPct = totalRev > 0 ? ((repeatRev / totalRev) * 100).toFixed(1) : '0';

  const revGrowthNum = parseNumericValue(prior_period_comparison?.revenue_growth_pct);
  const orderGrowthNum = parseNumericValue(prior_period_comparison?.order_growth_pct);
  const aovGrowthNum = parseNumericValue(prior_period_comparison?.aov_growth_pct);

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-base font-semibold text-gray-900">Revenue & Period Trajectory</h3>
        <p className="text-xs text-gray-500 mt-0.5">Period-over-period comparison & customer breakdown</p>
      </div>

      <div className="p-6 space-y-6">
        {/* Period comparison stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div className="text-xs font-medium text-gray-500">Revenue Growth</div>
            <div className="mt-1 flex items-baseline gap-2">
              <span
                className={`text-xl font-bold ${(revGrowthNum ?? 0) >= 0
                  ? 'text-emerald-600'
                  : 'text-rose-600'
                  }`}
              >
                {formatGrowthRate(prior_period_comparison?.revenue_growth_pct)}
              </span>
              <span className="text-xs text-gray-400">vs prior period</span>
            </div>
            <div className="text-[11px] text-gray-500 mt-1">
              Prior: {formatCurrency(prior_period_comparison?.prior_revenue || 0, currency)}
            </div>
          </div>

          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div className="text-xs font-medium text-gray-500">Order Volume Growth</div>
            <div className="mt-1 flex items-baseline gap-2">
              <span
                className={`text-xl font-bold ${(orderGrowthNum ?? 0) >= 0
                  ? 'text-emerald-600'
                  : 'text-rose-600'
                  }`}
              >
                {formatGrowthRate(prior_period_comparison?.order_growth_pct)}
              </span>
              <span className="text-xs text-gray-400">vs prior period</span>
            </div>
            <div className="text-[11px] text-gray-500 mt-1">
              Prior: {(prior_period_comparison?.prior_orders || 0).toLocaleString()} orders
            </div>
          </div>

          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div className="text-xs font-medium text-gray-500">AOV Shift</div>
            <div className="mt-1 flex items-baseline gap-2">
              <span
                className={`text-xl font-bold ${(aovGrowthNum ?? 0) >= 0
                  ? 'text-emerald-600'
                  : 'text-rose-600'
                  }`}
              >
                {formatGrowthRate(prior_period_comparison?.aov_growth_pct)}
              </span>
              <span className="text-xs text-gray-400">vs prior period</span>
            </div>
            <div className="text-[11px] text-gray-500 mt-1">
              Prior: {formatCurrency(prior_period_comparison?.prior_average_order_value || 0, currency)}
            </div>
          </div>
        </div>

        {/* Customer revenue split bar */}
        <div>
          <div className="flex justify-between items-center text-xs font-medium text-gray-700 mb-1.5">
            <span>Customer Revenue Composition</span>
            <span className="text-gray-500">
              New: {newPct}% • Repeat: {repeatPct}%
            </span>
          </div>

          <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden flex">
            <div className="bg-indigo-600 h-full" style={{ width: `${newPct}%` }} title={`New: ${newPct}%`} />
            <div className="bg-emerald-500 h-full" style={{ width: `${repeatPct}%` }} title={`Repeat: ${repeatPct}%`} />
          </div>

          <div className="grid grid-cols-2 gap-4 mt-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-600" />
              <div>
                <div className="font-semibold text-gray-800">
                  {formatCurrency(newRev, currency)}
                </div>
                <div className="text-[11px] text-gray-500">
                  New Customer ({customer_revenue_breakdown?.new_customer_order_count || 0} orders)
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <div>
                <div className="font-semibold text-gray-800">
                  {formatCurrency(repeatRev, currency)}
                </div>
                <div className="text-[11px] text-gray-500">
                  Repeat Customer ({customer_revenue_breakdown?.repeat_customer_order_count || 0} orders)
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
