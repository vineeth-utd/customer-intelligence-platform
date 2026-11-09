import { useMerchantFeatures } from '../../hooks/queries';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';

export function MerchantFeatures({ merchantId }: { merchantId: string }) {
  const { data, isLoading, isError, refetch } = useMerchantFeatures(merchantId);

  if (isLoading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <LoadingSpinner message="Loading feature entitlements..." />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <ErrorMessage message="Failed to load feature entitlements." retry={() => refetch()} />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-white p-8 rounded-lg shadow text-center">
        <p className="text-gray-500 text-sm">No platform features registered for this merchant.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-base font-semibold text-gray-900">Feature Entitlements & Adoption</h3>
        <p className="text-xs text-gray-500 mt-0.5">Entitled vs enabled platform features</p>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Feature
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Category
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Entitled
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Enabled
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((feature) => (
              <tr key={feature.feature_id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div className="font-medium text-gray-900">{feature.feature_name}</div>
                  <div className="text-xs text-gray-500 font-mono mt-0.5">{feature.feature_key}</div>
                  {feature.description && (
                    <div className="text-xs text-gray-400 mt-1">{feature.description}</div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500 capitalize">
                  {feature.feature_category.replace(/_/g, ' ')}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      feature.is_entitled
                        ? 'bg-blue-50 text-blue-700 border border-blue-200'
                        : 'bg-gray-100 text-gray-500 border border-gray-200'
                    }`}
                  >
                    {feature.is_entitled ? 'Entitled' : 'Not Entitled'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      feature.is_enabled
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-gray-100 text-gray-500 border border-gray-200'
                    }`}
                  >
                    {feature.is_enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

