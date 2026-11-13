import { Link, useSearchParams } from 'react-router-dom';
import { useShopper, useMerchant } from '../../hooks/queries';
import { useAuth } from '../../context';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';

import { ShopperProfileCard } from './ShopperProfileCard';
import { ShopperSegmentsCard } from './ShopperSegmentsCard';
import { ShopperJourneyTimeline } from './ShopperJourneyTimeline';
import { ShopperOrders } from './ShopperOrders';
import { ShopperActivityLog } from './ShopperActivityLog';

type ShopperTabKey = 'overview' | 'journeys' | 'orders' | 'activity';

interface ShopperOverviewProps {
  merchantId: string;
  shopperId: string;
}

export function ShopperOverview({ merchantId, shopperId }: ShopperOverviewProps) {
  const { isInternal } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const validTabs: ShopperTabKey[] = ['overview', 'journeys', 'orders', 'activity'];
  const tabParam = searchParams.get('tab') as ShopperTabKey | null;
  const activeTab = tabParam && validTabs.includes(tabParam) ? tabParam : 'overview';

  const handleTabChange = (key: ShopperTabKey) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (key === 'overview') {
          next.delete('tab');
        } else {
          next.set('tab', key);
        }
        return next;
      },
      { replace: true }
    );
  };

  const {
    data: shopper,
    isLoading: loadingShopper,
    isError: errorShopper,
    error: shopperError,
    refetch: refetchShopper,
  } = useShopper(merchantId, shopperId);

  const { data: merchant } = useMerchant(merchantId);

  if (loadingShopper) {
    return (
      <div className="bg-white p-12 rounded-lg shadow flex items-center justify-center min-h-[400px]">
        <LoadingSpinner message="Loading shopper intelligence..." />
      </div>
    );
  }

  if (errorShopper || !shopper) {
    const message =
      shopperError instanceof Error ? shopperError.message : 'Failed to load shopper details.';
    return (
      <div className="bg-white p-8 rounded-lg shadow">
        <ErrorMessage message={message} retry={() => refetchShopper()} />
      </div>
    );
  }

  const displayName =
    shopper.first_name || shopper.last_name
      ? `${shopper.first_name || ''} ${shopper.last_name || ''}`.trim()
      : 'Anonymous / Guest Shopper';

  const locationString =
    [shopper.city, shopper.state, shopper.country].filter(Boolean).join(', ') ||
    'Location not recorded';

  const tabs: { key: ShopperTabKey; label: string }[] = [
    { key: 'overview', label: 'Overview & Profile' },
    { key: 'journeys', label: 'Shopper Journeys' },
    { key: 'orders', label: 'Purchase History' },
    { key: 'activity', label: 'Storefront Activity' },
  ];

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation Bar */}
      <nav className="flex flex-wrap items-center text-xs text-gray-500 gap-2 mb-2">
        {isInternal ? (
          <>
            <Link to="/merchants" className="hover:text-indigo-600 transition-colors">
              Merchants
            </Link>
            <span>&rsaquo;</span>
            <Link
              to={`/merchants/${merchantId}`}
              className="hover:text-indigo-600 transition-colors font-medium text-gray-700"
            >
              {merchant?.merchant_name || 'Store Overview'}
            </Link>
          </>
        ) : (
          <Link
            to={`/merchants/${merchantId}`}
            className="hover:text-indigo-600 transition-colors font-medium text-gray-700"
          >
            {merchant?.merchant_name || 'Store Intelligence'}
          </Link>
        )}
        <span>&rsaquo;</span>
        <Link
          to={`/merchants/${merchantId}?tab=shoppers`}
          className="hover:text-indigo-600 transition-colors text-gray-600"
        >
          Shoppers
        </Link>
        <span>&rsaquo;</span>
        <span className="font-semibold text-gray-900 truncate max-w-xs">{displayName}</span>
      </nav>

      {/* Shopper Identity Header */}
      <div className="bg-white p-6 rounded-lg shadow border-l-4 border-indigo-600 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-2xl font-bold text-gray-900">{displayName}</h2>
            <span
              title={shopper.shopper_id}
              className="text-xs font-mono bg-gray-100 text-gray-700 px-2 py-0.5 rounded border border-gray-200"
            >
              ID: {shopper.shopper_id}
            </span>
          </div>

          <p className="text-xs text-gray-500 mt-2 flex flex-wrap gap-x-5 gap-y-1">
            <span>
              Email: <strong className="text-gray-700">{shopper.email || 'None'}</strong>
            </span>
            <span>
              Location: <strong className="text-gray-700">{locationString}</strong>
            </span>
            {shopper.timezone && (
              <span>
                Timezone: <strong className="text-gray-700">{shopper.timezone}</strong>
              </span>
            )}
            <span>
              First Seen:{' '}
              <strong className="text-gray-700">
                {shopper.first_seen_at
                  ? new Date(shopper.first_seen_at).toLocaleDateString()
                  : 'N/A'}
              </strong>
            </span>
            <span>
              Last Seen:{' '}
              <strong className="text-gray-700">
                {shopper.last_seen_at ? new Date(shopper.last_seen_at).toLocaleDateString() : 'N/A'}
              </strong>
            </span>
          </p>
        </div>

        <div>
          <Link
            to={`/merchants/${merchantId}?tab=shoppers`}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 bg-gray-50 hover:bg-gray-100 px-3 py-2 rounded-md border border-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            &larr; Back to Store Overview
          </Link>
        </div>
      </div>

      {/* Primary Navigation Tabs */}
      <div className="border-b border-gray-200 bg-white px-6 rounded-t-lg shadow-sm">
        <nav className="-mb-px flex space-x-8 overflow-x-auto" aria-label="Shopper Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => handleTabChange(tab.key)}
              className={`whitespace-nowrap shrink-0 py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors focus:outline-none focus:ring-1 focus:ring-indigo-500 ${activeTab === tab.key
                ? 'border-indigo-500 text-indigo-600 font-semibold'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Panels */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <ShopperProfileCard merchantId={merchantId} shopperId={shopperId} currency={merchant?.store_currency} />
          <ShopperSegmentsCard merchantId={merchantId} shopperId={shopperId} />
        </div>
      )}

      {activeTab === 'journeys' && (
        <div className="space-y-6">
          <ShopperJourneyTimeline merchantId={merchantId} shopperId={shopperId} />
        </div>
      )}

      {activeTab === 'orders' && (
        <div className="space-y-6">
          <ShopperOrders merchantId={merchantId} shopperId={shopperId} />
        </div>
      )}

      {activeTab === 'activity' && (
        <div className="space-y-6">
          <ShopperActivityLog merchantId={merchantId} shopperId={shopperId} />
        </div>
      )}
    </div>
  );
}

