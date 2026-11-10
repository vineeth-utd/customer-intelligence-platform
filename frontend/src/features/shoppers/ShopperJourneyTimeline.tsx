import { useState } from 'react';
import { useShopperJourneys, useShopperJourneyDetail } from '../../hooks/queries';
import { StatusBadge } from '../../components/common/StatusBadge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import type { ShopperJourneyEventResponse } from '../../types';

interface ShopperJourneyTimelineProps {
  merchantId: string;
  shopperId: string;
}

const AUTHORITATIVE_EVENT_CONFIG: Record<
  string,
  { label: string; icon: string; category: 'storefront' | 'campaign' }
> = {
  // Storefront qualifying event types
  SESSION_STARTED: { label: 'Storefront Session Started', icon: '🌐', category: 'storefront' },
  SESSION_ENDED: { label: 'Storefront Session Ended', icon: '⏹️', category: 'storefront' },
  PRODUCT_VIEWED: { label: 'Product Viewed', icon: '👁️', category: 'storefront' },
  PRODUCT_SEARCHED: { label: 'Product Catalog Searched', icon: '🔍', category: 'storefront' },
  WISHLIST_ADDED: { label: 'Added to Wishlist', icon: '❤️', category: 'storefront' },
  WISHLIST_REMOVED: { label: 'Removed from Wishlist', icon: '🤍', category: 'storefront' },
  SAVE_FOR_LATER_ADDED: { label: 'Saved for Later', icon: '🔖', category: 'storefront' },
  SAVE_FOR_LATER_REMOVED: { label: 'Removed from Saved for Later', icon: '📑', category: 'storefront' },
  ADD_TO_CART: { label: 'Added Item to Cart', icon: '🛒', category: 'storefront' },
  REMOVE_FROM_CART: { label: 'Removed Item from Cart', icon: '🗑️', category: 'storefront' },
  CHECKOUT_STARTED: { label: 'Checkout Started', icon: '💳', category: 'storefront' },
  PURCHASE_COMPLETED: { label: 'Purchase Completed (Order Placed)', icon: '🎉', category: 'storefront' },
  RECOMMENDATION_VIEWED: { label: 'Recommendation Viewed', icon: '✨', category: 'storefront' },
  RECOMMENDATION_CLICKED: { label: 'Recommendation Clicked', icon: '👉', category: 'storefront' },

  // Campaign qualifying event types
  EMAIL_OPENED: { label: 'Marketing Email Opened', icon: '✉️', category: 'campaign' },
  EMAIL_CLICKED: { label: 'Marketing Email Clicked', icon: '🔗', category: 'campaign' },
  SMS_CLICKED: { label: 'SMS Marketing Link Clicked', icon: '📱', category: 'campaign' },
  PUSH_OPENED: { label: 'Push Notification Opened', icon: '🔔', category: 'campaign' },
  AD_CLICKED: { label: 'Marketing Ad Clicked', icon: '📢', category: 'campaign' },
};

function formatDuration(startedAt: string, endedAt: string | null): string {
  if (!endedAt) return 'In Progress (Active Journey)';
  const diffMs = Math.max(0, new Date(endedAt).getTime() - new Date(startedAt).getTime());
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;

  if (days > 0) {
    return `${days}d ${remainingHours}h`;
  }
  const mins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
  return `${hours}h ${mins}m`;
}

export function ShopperJourneyTimeline({ merchantId, shopperId }: ShopperJourneyTimelineProps) {
  const {
    data: journeys,
    isLoading: loadingJourneys,
    isError: errorJourneys,
    refetch: refetchJourneys,
  } = useShopperJourneys(merchantId, shopperId);

  const [selectedJourneyId, setSelectedJourneyId] = useState<string | null>(null);
  const [showTechnicalLineage, setShowTechnicalLineage] = useState(false);

  const activeJourneyId =
    selectedJourneyId || (journeys && journeys.length > 0 ? journeys[0].journey_id : '');

  const {
    data: journeyDetail,
    isLoading: loadingDetail,
    isError: errorDetail,
    refetch: refetchDetail,
  } = useShopperJourneyDetail(merchantId, shopperId, activeJourneyId);

  if (loadingJourneys) {
    return (
      <div className="bg-white p-6 rounded-lg shadow min-h-[300px] flex items-center justify-center">
        <LoadingSpinner message="Loading shopper behavioural journeys..." />
      </div>
    );
  }

  if (errorJourneys || !journeys) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <ErrorMessage
          message="Failed to load shopper journeys."
          retry={() => refetchJourneys()}
        />
      </div>
    );
  }

  if (journeys.length === 0) {
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
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
          />
        </svg>
        <h4 className="text-base font-medium text-gray-900">No Shopper Journeys Recorded</h4>
        <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
          No 7-day multi-session behavioural journeys have been recorded for this shopper yet.
        </p>
      </div>
    );
  }

  const currentJourney = journeys.find((j) => j.journey_id === activeJourneyId) || journeys[0];

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden space-y-0">
      {/* Journey Header & Selector */}
      <div className="px-6 py-5 border-b border-gray-200 flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-medium text-gray-900">Shopper Behavioural Journey</h3>
            <StatusBadge status={currentJourney.journey_status} type="journey" />
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            Ordered multi-session touchpoint sequence within a 7-day conversion window
          </p>
        </div>

        <div className="flex items-center gap-3">
          {journeys.length > 1 && (
            <div className="flex items-center gap-2">
              <label htmlFor="journey-select" className="text-xs font-medium text-gray-500">
                Select Journey:
              </label>
              <select
                id="journey-select"
                value={activeJourneyId}
                onChange={(e) => setSelectedJourneyId(e.target.value)}
                className="text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-medium text-gray-700"
              >
                {journeys.map((j, idx) => (
                  <option key={j.journey_id} value={j.journey_id}>
                    Journey #{journeys.length - idx} ({j.journey_status} -{' '}
                    {new Date(j.started_at).toLocaleDateString()})
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            type="button"
            onClick={() => setShowTechnicalLineage(!showTechnicalLineage)}
            className="text-xs text-gray-600 hover:text-gray-900 px-2.5 py-1.5 rounded border border-gray-300 hover:bg-gray-50 transition-colors"
          >
            {showTechnicalLineage ? 'Hide Technical Lineage' : 'Show Technical Lineage'}
          </button>
        </div>
      </div>

      {/* Journey Summary Strip */}
      <div className="p-6 bg-gray-50/70 border-b border-gray-200">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div>
            <span className="text-gray-500 font-medium block">Entry Source:</span>
            <span className="font-semibold text-gray-900 font-mono mt-0.5 inline-block">
              {currentJourney.entry_source || 'direct'}
            </span>
          </div>

          <div>
            <span className="text-gray-500 font-medium block">Started At:</span>
            <span className="font-semibold text-gray-900 mt-0.5 inline-block">
              {new Date(currentJourney.started_at).toLocaleString()}
            </span>
          </div>

          <div>
            <span className="text-gray-500 font-medium block">Ended At:</span>
            <span className="font-semibold text-gray-900 mt-0.5 inline-block">
              {currentJourney.ended_at
                ? new Date(currentJourney.ended_at).toLocaleString()
                : 'Active / Open'}
            </span>
          </div>

          <div>
            <span className="text-gray-500 font-medium block">Window Span:</span>
            <span className="font-semibold text-gray-900 mt-0.5 inline-block">
              {formatDuration(currentJourney.started_at, currentJourney.ended_at)}
            </span>
          </div>
        </div>

        {/* Conversion Banner if Converted */}
        {currentJourney.converted && currentJourney.order_id && (
          <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between text-xs text-emerald-800">
            <div className="flex items-center gap-2">
              <span className="text-base">🎉</span>
              <span>
                <strong>Journey Converted:</strong> This journey resulted in completed Order{' '}
                <code className="bg-emerald-100 px-1 py-0.5 rounded font-mono text-[11px] text-emerald-900">
                  {currentJourney.order_id}
                </code>
              </span>
            </div>
            <span className="font-semibold text-emerald-700 bg-emerald-100/60 px-2 py-0.5 rounded">
              Conversion Closes Journey
            </span>
          </div>
        )}

        {/* Non-Converting Expiration Banner */}
        {currentJourney.journey_status === 'NON_CONVERTING' && (
          <div className="mt-4 p-3 bg-slate-100 border border-slate-200 rounded-lg text-xs text-slate-700 flex items-center gap-2">
            <span className="text-base">⏱️</span>
            <span>
              <strong>7-Day Window Expired:</strong> No purchase occurred within 7 days of the first
              session. Journey closed deterministically.
            </span>
          </div>
        )}
      </div>

      {/* Chronological Timeline Body */}
      <div className="p-6">
        <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-6">
          Chronological Touchpoints ({journeyDetail?.events.length || 0} Events)
        </h4>

        {loadingDetail ? (
          <div className="py-12 flex justify-center">
            <LoadingSpinner message="Loading chronological journey touchpoints..." />
          </div>
        ) : errorDetail || !journeyDetail ? (
          <ErrorMessage
            message="Failed to load journey touchpoint events."
            retry={() => refetchDetail()}
          />
        ) : journeyDetail.events.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            No events recorded in this journey.
          </p>
        ) : (
          <div className="relative pl-6 border-l-2 border-indigo-100 space-y-6">
            {journeyDetail.events.map((event: ShopperJourneyEventResponse) => {
              const config = AUTHORITATIVE_EVENT_CONFIG[event.event_type] || {
                label: event.event_type.replace(/_/g, ' '),
                icon: '📌',
                category: event.source_event_category === 'campaign' ? 'campaign' : 'storefront',
              };

              const isCampaign = config.category === 'campaign';

              return (
                <div key={event.journey_event_id} className="relative group">
                  {/* Timeline marker */}
                  <div
                    className={`absolute -left-[31px] top-1 w-6 h-6 rounded-full flex items-center justify-center text-xs shadow-sm border ${
                      isCampaign
                        ? 'bg-purple-50 text-purple-700 border-purple-300'
                        : 'bg-indigo-50 text-indigo-700 border-indigo-300'
                    }`}
                  >
                    <span>{config.icon}</span>
                  </div>

                  <div
                    className={`p-4 rounded-lg border transition-shadow ${
                      isCampaign
                        ? 'bg-purple-50/20 border-purple-100 hover:border-purple-200'
                        : 'bg-white border-gray-100 hover:border-indigo-100'
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-gray-900">{config.label}</span>
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                            isCampaign
                              ? 'bg-purple-100 text-purple-700 border-purple-200'
                              : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                          }`}
                        >
                          {isCampaign ? 'Campaign Touchpoint' : 'Storefront Action'}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        <span className="font-mono text-[11px] bg-gray-100 px-1.5 py-0.5 rounded">
                          #{event.sequence_number}
                        </span>
                        <span>{new Date(event.event_timestamp).toLocaleString()}</span>
                      </div>
                    </div>

                    {/* Optional Collapsed Technical Lineage */}
                    {showTechnicalLineage && (
                      <div className="mt-3 pt-2 border-t border-gray-100 text-[11px] text-gray-400 font-mono grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <div>
                          <span className="text-gray-500">Event Type:</span> {event.event_type}
                        </div>
                        <div>
                          <span className="text-gray-500">Source Category:</span>{' '}
                          {event.source_event_category}
                        </div>
                        <div className="sm:col-span-2">
                          <span className="text-gray-500">Source Event ID:</span>{' '}
                          {event.source_event_id}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

