import { FunnelChart } from '../../components/charts/FunnelChart';
import type { ConversionFunnelResult } from '../../types';

interface MerchantFunnelCardProps {
  funnel: ConversionFunnelResult;
}

export function MerchantFunnelCard({ funnel }: MerchantFunnelCardProps) {
  const secondary = funnel.secondary_engagement || {};

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h3 className="text-base font-semibold text-gray-900">Conversion Funnel & Drop-Off</h3>
          <p className="text-xs text-gray-500 mt-0.5">Session-to-purchase funnel stages</p>
        </div>
        <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-1 rounded">
          Overall: {(funnel.overall_conversion_rate * 100).toFixed(2)}%
        </span>
      </div>

      <div className="p-6">
        <FunnelChart stages={funnel.stages} />

        {/* Abandonment rates */}
        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100 text-xs">
          <div className="p-3 bg-gray-50 rounded-lg">
            <span className="text-gray-500">Cart Abandonment Rate</span>
            <div className="text-lg font-bold text-gray-900 mt-0.5">
              {(funnel.cart_abandonment_rate * 100).toFixed(1)}%
            </div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <span className="text-gray-500">Checkout Abandonment Rate</span>
            <div className="text-lg font-bold text-gray-900 mt-0.5">
              {(funnel.checkout_abandonment_rate * 100).toFixed(1)}%
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

