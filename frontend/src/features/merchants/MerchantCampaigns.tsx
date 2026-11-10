import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCampaigns } from '../../hooks/queries/useCampaignQueries';
import { useMerchantCampaignAnalytics } from '../../hooks/queries/useMerchantQueries';
import { StatusBadge } from '../../components/common/StatusBadge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { Pagination } from '../../components/common/Pagination';
import type { CampaignStatus } from '../../types';

export function MerchantCampaigns({ merchantId }: { merchantId: string }) {
  const navigate = useNavigate();
  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | undefined>(undefined);
  const limit = 10;

  useEffect(() => {
    setOffset(0);
  }, [merchantId, statusFilter]);

  const {
    data: campaignsData,
    isLoading: loadingCampaigns,
    isError: errorCampaigns,
    refetch: refetchCampaigns,
  } = useCampaigns(merchantId, limit, offset, statusFilter);

  const { data: analyticsList } = useMerchantCampaignAnalytics(merchantId);

  // Map analytics summary by campaign_id for quick lookup
  const analyticsMap = new Map(
    (analyticsList || []).map((item) => [item.campaign_id, item])
  );

  const handleStatusChange = (status: CampaignStatus | undefined) => {
    setStatusFilter(status);
    setOffset(0);
  };

  if (loadingCampaigns) {
    return (
      <div className="bg-white p-6 rounded-lg shadow mb-8 h-[350px] flex items-center justify-center">
        <LoadingSpinner message="Loading campaigns..." />
      </div>
    );
  }

  if (errorCampaigns || !campaignsData) {
    return (
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <ErrorMessage message="Failed to load campaigns." retry={() => refetchCampaigns()} />
      </div>
    );
  }

  const { items, total } = campaignsData;

  return (
    <div className="bg-white rounded-lg shadow mb-8 overflow-hidden flex flex-col">
      {/* Header & Status Filter Bar */}
      <div className="px-6 py-5 border-b border-gray-200 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h3 className="text-lg font-medium text-gray-900">Campaigns & Marketing Intelligence</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Select a campaign to drill down into performance, attribution models, journey impact, and segment response
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-500 mr-1">Status:</span>
          {(
            [
              { label: 'All', value: undefined },
              { label: 'Active', value: 'active' as CampaignStatus },
              { label: 'Draft', value: 'draft' as CampaignStatus },
              { label: 'Completed', value: 'completed' as CampaignStatus },
            ] as const
          ).map((filter) => {
            const isSelected = statusFilter === filter.value;
            return (
              <button
                key={filter.label}
                type="button"
                onClick={() => handleStatusChange(filter.value)}
                className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                  isSelected
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {filter.label}
              </button>
            );
          })}
        </div>
      </div>

      {items.length === 0 ? (
        <div className="p-12 text-center text-gray-500">
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
              d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"
            />
          </svg>
          <p className="text-sm font-medium text-gray-900">No campaigns found</p>
          <p className="text-xs text-gray-500 mt-1">
            {statusFilter
              ? `No ${statusFilter} campaigns found for this merchant.`
              : 'This merchant has not created any marketing campaigns yet.'}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Campaign
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Delivered
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  CTR
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Orders
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Attributed Rev
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {items.map((campaign) => {
                const targetUrl = `/merchants/${merchantId}/campaigns/${campaign.campaign_id}`;
                const analytics = analyticsMap.get(campaign.campaign_id);

                return (
                  <tr
                    key={campaign.campaign_id}
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
                      <div className="flex items-center">
                        <div>
                          <Link
                            to={targetUrl}
                            className="text-sm font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {campaign.campaign_name}
                          </Link>
                          <div className="text-xs text-gray-500 mt-0.5 capitalize">
                            {campaign.campaign_type} • {campaign.campaign_medium}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={campaign.status} type="campaign" />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 text-right">
                      {analytics
                        ? analytics.delivered_count.toLocaleString()
                        : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 text-right">
                      {analytics
                        ? `${(analytics.click_through_rate * 100).toFixed(1)}%`
                        : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 text-right">
                      {analytics
                        ? analytics.attributed_order_count.toLocaleString()
                        : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 text-right">
                      {analytics
                        ? new Intl.NumberFormat('en-US', {
                            style: 'currency',
                            currency: 'USD',
                          }).format(analytics.attributed_revenue)
                        : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-xs">
                      <Link
                        to={targetUrl}
                        className="inline-flex items-center gap-1 font-semibold text-indigo-600 hover:text-indigo-900 bg-indigo-50 hover:bg-indigo-100 px-2.5 py-1 rounded transition-colors"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <span>View Intelligence</span>
                        <span aria-hidden="true">&rarr;</span>
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <Pagination
        total={total}
        limit={limit}
        offset={offset}
        onPageChange={setOffset}
      />
    </div>
  );
}
