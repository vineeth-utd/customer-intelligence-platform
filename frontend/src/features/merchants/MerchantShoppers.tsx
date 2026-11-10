import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMerchantShoppers } from '../../hooks/queries';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { Pagination } from '../../components/common/Pagination';

export function MerchantShoppers({ merchantId }: { merchantId: string }) {
  const navigate = useNavigate();
  const [offset, setOffset] = useState(0);
  const limit = 10;

  useEffect(() => {
    setOffset(0);
  }, [merchantId]);

  const { data, isLoading, isError, refetch } = useMerchantShoppers(merchantId, limit, offset);

  if (isLoading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow mb-8 h-[400px] flex items-center justify-center">
        <LoadingSpinner message="Loading shoppers..." />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <ErrorMessage message="Failed to load shoppers." retry={() => refetch()} />
      </div>
    );
  }

  if (data.items.length === 0 && offset === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Shoppers</h3>
        <p className="text-gray-500 text-center py-8">No shoppers found for this merchant.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow mb-8 overflow-hidden flex flex-col h-full">
      <div className="px-6 py-5 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-medium text-gray-900">Recent Shoppers</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Select a shopper to drill down into behavioral profiles and multi-session journeys
          </p>
        </div>
        <span className="text-xs font-medium text-gray-500">
          Total: <strong className="text-gray-900">{data.total}</strong>
        </span>
      </div>
      <div className="overflow-x-auto flex-1">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Shopper
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Location
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                First Seen
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Seen
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.items.map((shopper) => {
              const targetUrl = `/merchants/${merchantId}/shoppers/${shopper.shopper_id}`;
              const displayName =
                shopper.first_name || shopper.last_name
                  ? `${shopper.first_name || ''} ${shopper.last_name || ''}`.trim()
                  : 'Anonymous Shopper';

              return (
                <tr
                  key={shopper.shopper_id}
                  className="hover:bg-indigo-50/40 cursor-pointer transition-colors group focus-within:bg-indigo-50/50"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      navigate(targetUrl);
                    }
                  }}
                  onClick={() => navigate(targetUrl)}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Link
                      to={targetUrl}
                      onClick={(e) => e.stopPropagation()}
                      className="text-sm font-semibold text-indigo-600 hover:text-indigo-900 focus:outline-none focus:underline"
                    >
                      {displayName}
                    </Link>
                    <div className="text-xs text-gray-500 font-mono mt-0.5">
                      {shopper.email || 'No email provided'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {[shopper.city, shopper.state, shopper.country].filter(Boolean).join(', ') ||
                      'Unknown'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {shopper.first_seen_at
                      ? new Date(shopper.first_seen_at).toLocaleDateString()
                      : 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {shopper.last_seen_at
                      ? new Date(shopper.last_seen_at).toLocaleDateString()
                      : 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                    <Link
                      to={targetUrl}
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-2.5 py-1 rounded transition-colors"
                    >
                      Drill Down &rarr;
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Pagination total={data.total} limit={limit} offset={offset} onPageChange={setOffset} />
    </div>
  );
}
