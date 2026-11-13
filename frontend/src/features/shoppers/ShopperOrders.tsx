import { useState } from 'react';
import { useShopperOrders } from '../../hooks/queries';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { Pagination } from '../../components/common/Pagination';
import { StatusBadge } from '../../components/common/StatusBadge';
import { formatCurrency } from '../../utils';

interface ShopperOrdersProps {
  merchantId: string;
  shopperId: string;
}

export function ShopperOrders({ merchantId, shopperId }: ShopperOrdersProps) {
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const { data, isLoading, isError, refetch } = useShopperOrders(
    merchantId,
    shopperId,
    limit,
    offset
  );

  if (isLoading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow min-h-[300px] flex items-center justify-center">
        <LoadingSpinner message="Loading shopper purchase history..." />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <ErrorMessage message="Failed to load orders." retry={() => refetch()} />
      </div>
    );
  }

  if (data.items.length === 0 && offset === 0) {
    return (
      <div className="bg-white p-12 rounded-lg shadow text-center">
        <svg
          className="w-12 h-12 text-gray-300 mx-auto mb-3"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
          />
        </svg>
        <h4 className="text-base font-medium text-gray-900">No Purchase History</h4>
        <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
          This shopper has not placed any orders with this store yet.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden flex flex-col h-full">
      <div className="px-6 py-5 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-medium text-gray-900">Purchase History</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Historical orders placed by this shopper under this store
          </p>
        </div>
        <span className="text-xs font-medium text-gray-500">
          Total Orders: <strong className="text-gray-900">{data.total}</strong>
        </span>
      </div>

      <div className="overflow-x-auto flex-1">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Order ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Placed At
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Completed / Cancelled
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Total Amount
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200 text-xs">
            {data.items.map((order) => (
              <tr key={order.order_id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap font-mono text-gray-800 font-medium">
                  {order.order_id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                  {new Date(order.placed_at).toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <StatusBadge status={order.order_status} type="general" />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                  {order.completed_at
                    ? `Completed: ${new Date(order.completed_at).toLocaleDateString()}`
                    : order.cancelled_at
                    ? `Cancelled: ${new Date(order.cancelled_at).toLocaleDateString()}`
                    : 'Pending'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right font-bold text-gray-900">
                  {formatCurrency(order.total_amount, order.currency)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination total={data.total} limit={limit} offset={offset} onPageChange={setOffset} />
    </div>
  );
}

