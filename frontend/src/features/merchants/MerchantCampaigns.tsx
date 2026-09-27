import { useMerchantCampaignAnalytics } from '../../hooks/queries';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';

export function MerchantCampaigns({ merchantId }: { merchantId: string }) {
  const { data, isLoading, isError, refetch } = useMerchantCampaignAnalytics(merchantId);

  if (isLoading) {
    return <div className="bg-white p-6 rounded-lg shadow mb-8"><LoadingSpinner message="Loading campaigns..." /></div>;
  }

  if (isError || !data) {
    return <div className="bg-white p-6 rounded-lg shadow mb-8"><ErrorMessage message="Failed to load campaigns." retry={() => refetch()} /></div>;
  }

  if (data.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Campaign Performance</h3>
        <p className="text-gray-500 text-center py-8">No campaigns found for this merchant.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow mb-8 overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">Campaign Performance</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Campaign</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Delivered</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Open Rate</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">CTR</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Orders</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Revenue</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((campaign) => (
              <tr key={campaign.campaign_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">{campaign.campaign_name}</div>
                  <div className="text-sm text-gray-500">{campaign.campaign_type} • {campaign.campaign_medium}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">{campaign.status.replace('_', ' ')}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">{campaign.delivered_count.toLocaleString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">{(campaign.open_rate * 100).toFixed(1)}%</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">{(campaign.click_through_rate * 100).toFixed(1)}%</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">{campaign.attributed_order_count.toLocaleString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                  {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(campaign.attributed_revenue)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
