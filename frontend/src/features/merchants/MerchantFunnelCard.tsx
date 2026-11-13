import { FunnelChart } from '../../components/charts/FunnelChart';
import type { ConversionFunnelResult } from '../../types';
import { formatPercent } from '../../utils';

interface MerchantFunnelCardProps {
  funnel: ConversionFunnelResult;
}

export function MerchantFunnelCard({ funnel }: MerchantFunnelCardProps) {
  const secondary = funnel.secondary_engagement || {};
  const hasActivity = Boolean(funnel.stages) && funnel.stages.some((s) => s.count > 0);

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h3 className="text-base font-semibold text-gray-900">Conversion Funnel & Drop-Off</h3>
          <p className="text-xs text-gray-500 mt-0.5">Session-to-purchase funnel stages</p>
        </div>
        <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-1 rounded">
          Overall: {formatPercent(funnel.overall_conversion_rate, 2)}
        </span>
      </div>

      <div className="p-6">
        {hasActivity ? (
          <FunnelChart stages={funnel.stages} />
        ) : (
          <div className="py-12 text-center text-gray-500 text-xs flex flex-col items-center justify-center">
            <svg className="w-10 h-10 text-gray-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            <p className="font-medium text-gray-700">No session funnel activity in the selected period</p>
            <p className="text-gray-400 mt-1 max-w-xs">
              No storefront sessions progressed through discovery, cart, or checkout during this date range.
            </p>
          </div>
        )}

        {/* Abandonment rates */}
        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100 text-xs">
          <div className="p-3 bg-gray-50 rounded-lg">
            <span className="text-gray-500">Cart Abandonment Rate</span>
            <div className="text-lg font-bold text-gray-900 mt-0.5">
              {formatPercent(funnel.cart_abandonment_rate, 1)}
            </div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <span className="text-gray-500">Checkout Abandonment Rate</span>
            <div className="text-lg font-bold text-gray-900 mt-0.5">
              {formatPercent(funnel.checkout_abandonment_rate, 1)}
            </div>
          </div>
        </div>

        {/* Secondary micro-conversions */}
        {Object.keys(secondary).length > 0 && (
          <div className="mt-4 pt-3 border-t border-gray-100 flex flex-wrap gap-4 text-xs text-gray-600">
            <span className="font-medium text-gray-700">Secondary Engagement:</span>
            {Object.entries(secondary).map(([key, val]) => (
              <span key={key} className="bg-gray-100 px-2 py-0.5 rounded text-[11px] text-gray-700">
                {key.replace(/_/g, ' ')}: <strong className="text-gray-900">{val.toLocaleString()}</strong>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

