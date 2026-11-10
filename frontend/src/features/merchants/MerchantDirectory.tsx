import { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMerchants } from '../../hooks/queries';
import { StatusBadge } from '../../components/common/StatusBadge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { Pagination } from '../../components/common/Pagination';

export function MerchantDirectory() {
  const navigate = useNavigate();
  const [offset, setOffset] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const limit = 20;

  const { data, isLoading, isError, refetch } = useMerchants(limit, offset);

  const filteredItems = useMemo(() => {
    if (!data?.items) return [];
    if (!searchQuery.trim()) return data.items;
    const q = searchQuery.toLowerCase().trim();
    return data.items.filter(
      (m) =>
        m.merchant_name.toLowerCase().includes(q) ||
        m.shopify_store_id.toLowerCase().includes(q) ||
        m.email.toLowerCase().includes(q)
    );
  }, [data?.items, searchQuery]);

  if (isLoading) {
    return (
      <div className="bg-white p-12 rounded-lg shadow flex items-center justify-center min-h-[350px]">
        <LoadingSpinner message="Loading merchant directory..." />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-white p-8 rounded-lg shadow">
        <ErrorMessage message="Failed to load merchant directory." retry={() => refetch()} />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden flex flex-col">
      {/* Header & Controls */}
      <div className="px-6 py-5 border-b border-gray-200 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Merchant Directory</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Platform-wide merchant stores with operational status, Shopify domains, and intelligence drill-down.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <input
              type="text"
              placeholder="Search by name, store, or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="text-xs border border-gray-300 rounded-md pl-8 pr-3 py-1.5 w-64 focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white"
            />
            <svg
              className="w-4 h-4 text-gray-400 absolute left-2.5 top-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>

          <span className="text-xs font-medium text-gray-500 bg-gray-50 px-2.5 py-1 rounded border border-gray-200">
            Total Stores: <strong className="text-gray-900">{data.total}</strong>
          </span>
        </div>
      </div>

      {/* Directory Table */}
      {filteredItems.length === 0 ? (
        <div className="py-16 text-center text-gray-500">
          <p className="text-sm font-medium">No merchants matching your search.</p>
          <p className="text-xs text-gray-400 mt-1">Try clearing your search query to see all merchants.</p>
        </div>
      ) : (
        <div className="overflow-x-auto flex-1 relative">
          <table className="min-w-[800px] w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Store / Merchant
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Shopify Domain
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Install Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Currency
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Active
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider sticky right-0 bg-gray-50 z-20 shadow-[-4px_0_6px_-2px_rgba(0,0,0,0.06)] border-l border-gray-200">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200 text-xs">
              {filteredItems.map((merchant) => {
                const targetUrl = `/merchants/${merchant.merchant_id}`;

                return (
                  <tr
                    key={merchant.merchant_id}
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
                        title={`Merchant ID: ${merchant.merchant_id}`}
                        className="text-sm font-semibold text-indigo-600 hover:text-indigo-900 focus:outline-none focus:underline"
                      >
                        {merchant.merchant_name}
                      </Link>
                      <div className="text-xs text-gray-500 font-mono mt-0.5">
                        {merchant.email}
                      </div>
                    </td>

                    <td className="px-6 py-4 whitespace-nowrap font-mono text-gray-700">
                      {merchant.shopify_store_id}
                    </td>

                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={merchant.app_install_status} type="install" />
                    </td>

                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-800 uppercase">
                      {merchant.store_currency}
                    </td>

                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {merchant.last_active_at
                        ? new Date(merchant.last_active_at).toLocaleDateString()
                        : 'Never recorded'}
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
      )}

      {/* Pagination */}
      <Pagination
        total={data.total}
        limit={limit}
        offset={offset}
        onPageChange={setOffset}
      />
    </div>
  );
}

