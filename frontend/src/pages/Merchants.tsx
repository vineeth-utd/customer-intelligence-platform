import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context';
import { MerchantSelector } from '../features/merchants/MerchantSelector';
import { MerchantOverview } from '../features/merchants/MerchantOverview';
import { MerchantDirectory } from '../features/merchants/MerchantDirectory';

export function Merchants() {
  const { merchantId: routeMerchantId } = useParams<{ merchantId?: string }>();
  const navigate = useNavigate();
  const { isMerchant, isInternal, merchantId: principalMerchantId } = useAuth();

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
            <h3 className="text-lg font-bold text-rose-900">403 Forbidden: Tenant Isolation Boundary</h3>
            <p className="mt-2 text-sm text-rose-700">
              You are authenticated as merchant <code className="bg-rose-100 px-1 py-0.5 rounded font-mono text-xs">{principalMerchantId}</code> and cannot access another merchant's intelligence.
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

    // Authenticated merchant viewing their own store
    const targetId = principalMerchantId;
    return (
      <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Store Intelligence Overview</h1>
          <p className="mt-1 text-xs text-gray-500">
            Real-time business performance, customer funnels, and store intelligence.
          </p>
        </div>
        <MerchantOverview merchantId={targetId} key={targetId} />
      </div>
    );
  }

  // INTERNAL scope: full merchant selector & navigation
  const activeMerchantId = routeMerchantId || null;

  return (
    <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Merchants</h1>
          <p className="mt-2 text-sm text-gray-600">
            Investigate performance, health, lifecycle journeys, and analytics for specific merchants.
          </p>
        </div>

        {isInternal && (
          <div className="w-full sm:w-auto">
            <MerchantSelector
              selectedMerchantId={activeMerchantId}
              onSelect={(id) => navigate(`/merchants/${id}`)}
            />
          </div>
        )}
      </div>

      {activeMerchantId ? (
        <MerchantOverview merchantId={activeMerchantId} key={activeMerchantId} />
      ) : (
        <MerchantDirectory />
      )}
    </div>
  );
}
