import { useState, useEffect } from 'react';
import { useMerchantOrders } from '../../hooks/queries';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { Pagination } from '../../components/common/Pagination';

export function MerchantOrders({ merchantId }: { merchantId: string }) {
  const [offset, setOffset] = useState(0);
  const limit = 10;
  
  useEffect(() => {
    setOffset(0);
  }, [merchantId]);
  
  const { data, isLoading, isError, refetch } = useMerchantOrders(merchantId, limit, offset);

  if (isLoading) {
    return <div className="bg-white p-6 rounded-lg shadow mb-8 h-[400px] flex items-center justify-center"><LoadingSpinner message="Loading orders..." /></div>;
  }

  if (isError || !data) {
    return <div className="bg-white p-6 rounded-lg shadow mb-8"><ErrorMessage message="Failed to load orders." retry={() => refetch()} /></div>;
  }

  if (data.items.length === 0 && offset === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Orders</h3>
        <p className="text-gray-500 text-center py-8">No orders found for this merchant.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow mb-8 overflow-hidden flex flex-col h-full">
      <div className="px-6 py-5 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">Recent Orders</h3>
      </div>
      <div className="overflow-x-auto flex-1">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Order ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Placed At</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Total Amount</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.items.map((order) => (
              <tr key={order.order_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                  {order.order_id.substring(0, 8)}...
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {new Date(order.placed_at).toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    order.order_status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                    order.order_status === 'CANCELLED' ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {order.order_status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                  {new Intl.NumberFormat('en-US', { style: 'currency', currency: order.currency }).format(order.total_amount)}
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
