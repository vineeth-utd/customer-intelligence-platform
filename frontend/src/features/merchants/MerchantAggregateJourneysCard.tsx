import type { ShopperJourneyAnalyticsResult } from '../../types';

interface MerchantAggregateJourneysCardProps {
  journeys: ShopperJourneyAnalyticsResult;
}

export function MerchantAggregateJourneysCard({ journeys }: MerchantAggregateJourneysCardProps) {
  const formatDuration = (seconds: number | null) => {
    if (seconds === null || seconds === undefined) return 'N/A';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h3 className="text-base font-semibold text-gray-900">Shopper Journey Aggregate Outcomes</h3>
          <p className="text-xs text-gray-500 mt-0.5">Multi-touch customer journeys & entry source attribution</p>
        </div>
        <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-1 rounded">
          Conv: {(journeys.journey_conversion_rate * 100).toFixed(1)}%
        </span>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="p-3 bg-gray-50 rounded-lg">
            <span className="text-xs text-gray-500 font-medium">Total Journeys</span>
            <div className="text-lg font-bold text-gray-900 mt-0.5">
              {journeys.total_journeys.toLocaleString()}
            </div>
          </div>
          <div className="p-3 bg-emerald-50 rounded-lg">
            <span className="text-xs text-emerald-700 font-medium">Converted</span>
            <div className="text-lg font-bold text-emerald-900 mt-0.5">
              {journeys.converted_journeys.toLocaleString()}
            </div>
          </div>
          <div className="p-3 bg-blue-50 rounded-lg">
            <span className="text-xs text-blue-700 font-medium">Open / Active</span>
            <div className="text-lg font-bold text-blue-900 mt-0.5">
              {journeys.open_journeys.toLocaleString()}
            </div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <span className="text-xs text-gray-500 font-medium">Avg Duration</span>
            <div className="text-lg font-bold text-gray-900 mt-0.5">
              {formatDuration(journeys.average_conversion_duration_seconds)}
            </div>
          </div>
        </div>

        {/* By entry source breakdown table */}
        {journeys.by_entry_source && journeys.by_entry_source.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
              Performance by Entry Source
            </h4>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-xs">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-gray-500">Entry Source</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-500">Journeys</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-500">Converted</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-500">Conversion Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {journeys.by_entry_source.map((source) => (
                    <tr key={source.entry_source} className="hover:bg-gray-50">
                      <td className="px-3 py-2 font-medium text-gray-800 capitalize">
                        {source.entry_source.replace(/_/g, ' ')}
                      </td>
                      <td className="px-3 py-2 text-right text-gray-600">
                        {source.total_journeys.toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-right text-emerald-600 font-medium">
                        {source.converted_journeys.toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-right font-semibold text-gray-900">
                        {(source.conversion_rate * 100).toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

