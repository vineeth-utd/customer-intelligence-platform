import { useState, useEffect } from 'react';
import { useMerchantShoppers } from '../../hooks/queries';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { Pagination } from '../../components/common/Pagination';

export function MerchantShoppers({ merchantId }: { merchantId: string }) {
  const [offset, setOffset] = useState(0);
  const limit = 10;
  
  useEffect(() => {
    setOffset(0);
  }, [merchantId]);
  
  const { data, isLoading, isError, refetch } = useMerchantShoppers(merchantId, limit, offset);

  if (isLoading) {
    return <div className="bg-white p-6 rounded-lg shadow mb-8 h-[400px] flex items-center justify-center"><LoadingSpinner message="Loading shoppers..." /></div>;
  }

  if (isError || !data) {
    return <div className="bg-white p-6 rounded-lg shadow mb-8"><ErrorMessage message="Failed to load shoppers." retry={() => refetch()} /></div>;
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
      <div className="px-6 py-5 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">Recent Shoppers</h3>
      </div>
      <div className="overflow-x-auto flex-1">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Shopper</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">First Seen</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Seen</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.items.map((shopper) => (
              <tr key={shopper.shopper_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">
                    {shopper.first_name || shopper.last_name ? `${shopper.first_name || ''} ${shopper.last_name || ''}` : 'Unknown'}
                  </div>
                  <div className="text-sm text-gray-500">{shopper.email || 'No email'}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {[shopper.city, shopper.state, shopper.country].filter(Boolean).join(', ') || 'Unknown'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {shopper.first_seen_at ? new Date(shopper.first_seen_at).toLocaleDateString() : 'N/A'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {shopper.last_seen_at ? new Date(shopper.last_seen_at).toLocaleDateString() : 'N/A'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination 
        total={data.total}
        limit={limit}
        offset={offset}
        onPageChange={setOffset}
      />
    </div>
  );
}
