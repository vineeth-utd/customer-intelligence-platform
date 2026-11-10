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
      <div className="bg-white p-12 rounded-lg shadow mb-8 text-center">
        <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
        <h3 className="text-lg font-medium text-gray-900 mb-1">No Shoppers Recorded</h3>
        <p className="text-gray-500 text-sm max-w-sm mx-auto">
          No customer records have engaged with this store yet. When shoppers visit your storefront or interact with campaigns, their profiles will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow mb-8 overflow-hidden flex flex-col h-full">
      <div className="px-6 py-5 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Shoppers & Customers</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Merchant-scoped shopper directory. Drill down into behavioral profiles, segment memberships, purchase histories, and multi-session journeys.
          </p>
        </div>
        <span className="text-xs font-medium text-gray-500">
          Total Shoppers: <strong className="text-gray-900">{data.total}</strong>
        </span>
      </div>
      <div className="overflow-x-auto flex-1 relative">
        <table className="min-w-[700px] w-full divide-y divide-gray-200">
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
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider sticky right-0 bg-gray-50 z-20 shadow-[-4px_0_6px_-2px_rgba(0,0,0,0.06)] border-l border-gray-200">
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
                      title={`Shopper ID: ${shopper.shopper_id}`}
                      className="text-sm font-semibold text-indigo-600 hover:text-indigo-900 focus:outline-none focus:underline"
                    >
                      {displayName}
                    </Link>
                    <div className="text-xs text-gray-500 font-mono mt-0.5" title={shopper.shopper_id}>
                      {shopper.email || `${shopper.shopper_id.substring(0, 12)}...`}
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
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm sticky right-0 bg-white group-hover:bg-indigo-50/90 group-focus-within:bg-indigo-50/90 z-10 shadow-[-4px_0_6px_-2px_rgba(0,0,0,0.06)] border-l border-gray-100">
                    <Link
                      to={targetUrl}
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 whitespace-nowrap"
                    >
                      <span>View Intelligence</span>
                      <span>&rarr;</span>
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
