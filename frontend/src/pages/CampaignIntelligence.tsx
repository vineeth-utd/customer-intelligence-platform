import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context';
import { CampaignOverview } from '../features/campaigns/CampaignOverview';

export function CampaignIntelligence() {
  const { merchantId: routeMerchantId, campaignId: routeCampaignId } = useParams<{
    merchantId?: string;
    campaignId?: string;
  }>();
  const navigate = useNavigate();
  const { isMerchant, merchantId: principalMerchantId } = useAuth();

  // For MERCHANT scope: enforce tenant boundary
  if (isMerchant && principalMerchantId) {
    if (routeMerchantId && routeMerchantId !== principalMerchantId) {
      return (
        <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
          <div className="bg-rose-50 border border-rose-200 rounded-lg p-8 text-center max-w-xl mx-auto my-12">
            <div className="w-12 h-12 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-rose-900">
              403 Forbidden: Tenant Isolation Boundary
            </h3>
            <p className="mt-2 text-sm text-rose-700">
              You are authenticated as merchant{' '}
              <code className="bg-rose-100 px-1 py-0.5 rounded font-mono text-xs">
                {principalMerchantId}
              </code>{' '}
              and cannot access another merchant&apos;s campaign intelligence.
            </p>
            <div className="mt-6">
              <button
                type="button"
                onClick={() => navigate(`/merchants/${principalMerchantId}`)}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
              >
                Return to My Store Overview
              </button>
            </div>
          </div>
        </div>
      );
    }
  }

  if (!routeMerchantId || !routeCampaignId) {
    return (
      <div className="max-w-7xl mx-auto p-12 text-center text-gray-500">
        Missing merchant or campaign identifier in URL.
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <CampaignOverview
        merchantId={routeMerchantId}
        campaignId={routeCampaignId}
        key={`${routeMerchantId}-${routeCampaignId}`}
      />
    </div>
  );
}

