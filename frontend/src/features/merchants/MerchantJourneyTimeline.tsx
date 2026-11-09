import { useState } from 'react';
import { useMerchantJourneys, useMerchantJourneyDetail } from '../../hooks/queries';
import { StatusBadge } from '../../components/common/StatusBadge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';

const EVENT_LABELS: Record<string, string> = {
  APP_INSTALLED: 'App Installed (Lifecycle Started)',
  APP_UNINSTALLED: 'App Uninstalled (Lifecycle Closed)',
  MERCHANT_CREATED: 'Store Profile Initialized',
  SUBSCRIPTION_STARTED: 'Subscription Activated',
  SUBSCRIPTION_RENEWED: 'Subscription Renewed',
  SUBSCRIPTION_UPGRADED: 'Subscription Upgraded',
  SUBSCRIPTION_DOWNGRADED: 'Subscription Downgraded',
  SUBSCRIPTION_CANCELLED: 'Subscription Cancelled',
  FEATURE_ENABLED: 'Platform Feature Enabled',
  FEATURE_DISABLED: 'Platform Feature Disabled',
  MERCHANT_CONFIGURATION_UPDATED: 'Store Configuration Updated',
  MERCHANT_LOGIN: 'Platform Dashboard Login',
  CAMPAIGN_CREATED: 'Marketing Campaign Created',
};

export function MerchantJourneyTimeline({ merchantId }: { merchantId: string }) {
  const { data: journeys, isLoading: loadingJourneys, isError: errorJourneys, refetch: refetchJourneys } =
    useMerchantJourneys(merchantId);

  const [selectedJourneyId, setSelectedJourneyId] = useState<string | null>(null);

  const activeJourneyId = selectedJourneyId || (journeys && journeys.length > 0 ? journeys[0].merchant_journey_id : '');

  const { data: journeyDetail, isLoading: loadingDetail, isError: errorDetail, refetch: refetchDetail } =
    useMerchantJourneyDetail(merchantId, activeJourneyId);

  if (loadingJourneys) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <LoadingSpinner message="Loading merchant lifecycle journeys..." />
      </div>
    );
  }

  if (errorJourneys || !journeys) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <ErrorMessage message="Failed to load merchant journeys." retry={() => refetchJourneys()} />
      </div>
    );
  }

  if (journeys.length === 0) {
    return (
      <div className="bg-white p-8 rounded-lg shadow text-center">
        <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        <h4 className="text-base font-medium text-gray-900">No Lifecycle Journeys</h4>
        <p className="text-xs text-gray-500 mt-1">
          No platform lifecycle events have been recorded for this merchant yet.
        </p>
      </div>
    );
  }

  const currentJourney = journeys.find((j) => j.merchant_journey_id === activeJourneyId) || journeys[0];

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex flex-wrap justify-between items-center gap-3">
        <div>
          <h3 className="text-lg font-medium text-gray-900">Merchant Lifecycle Journey</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Ordered platform lifecycle milestone sequence
          </p>
        </div>

        <div className="flex items-center gap-3">
          {journeys.length > 1 && (
            <select
              value={activeJourneyId}
              onChange={(e) => setSelectedJourneyId(e.target.value)}
              className="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {journeys.map((j, idx) => (
                <option key={j.merchant_journey_id} value={j.merchant_journey_id}>
                  Journey #{journeys.length - idx} ({j.journey_status} - {new Date(j.started_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          )}

          <StatusBadge status={currentJourney.journey_status} type="journey" />
        </div>
      </div>

      <div className="p-6">
        <div className="mb-6 grid grid-cols-1 sm:grid-cols-3 gap-4 p-3 bg-gray-50 rounded-lg border border-gray-100 text-xs">
          <div>
            <span className="text-gray-500 font-medium">Lifecycle Status:</span>{' '}
            <span className="font-semibold text-gray-900">{currentJourney.journey_status}</span>
          </div>
          <div>
            <span className="text-gray-500 font-medium">Started At:</span>{' '}
            <span className="text-gray-900">{new Date(currentJourney.started_at).toLocaleString()}</span>
          </div>
          <div>
            <span className="text-gray-500 font-medium">Ended At:</span>{' '}
            <span className="text-gray-900">
              {currentJourney.ended_at ? new Date(currentJourney.ended_at).toLocaleString() : 'Ongoing'}
            </span>
          </div>
        </div>

        {loadingDetail ? (
          <div className="py-8">
            <LoadingSpinner message="Loading milestone events..." />
          </div>
        ) : errorDetail || !journeyDetail ? (
          <ErrorMessage message="Failed to load journey milestone events." retry={() => refetchDetail()} />
        ) : journeyDetail.events.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-6">No milestone events found for this journey.</p>
        ) : (
          <div className="relative pl-6 sm:pl-8 border-l-2 border-indigo-100 space-y-6 my-4 ml-4">
            {journeyDetail.events.map((event) => {
              const friendlyLabel = EVENT_LABELS[event.event_type] || event.event_type.replace(/_/g, ' ');
              const isStart = event.event_type === 'APP_INSTALLED';
              const isEnd = event.event_type === 'APP_UNINSTALLED';

              return (
                <div key={event.merchant_journey_event_id} className="relative group">
                  {/* Timeline indicator node */}
                  <div
                    className={`absolute -left-[31px] sm:-left-[39px] top-0.5 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white border-2 border-white shadow-sm ${
                      isStart
                        ? 'bg-emerald-500'
                        : isEnd
                        ? 'bg-rose-500'
                        : 'bg-indigo-500'
                    }`}
                  >
                    {event.sequence_number}
                  </div>

                  <div className="bg-white p-3 rounded-lg border border-gray-200 hover:border-indigo-300 transition-colors shadow-xs">
                    <div className="flex flex-wrap items-center justify-between gap-1 mb-1">
                      <span className="text-sm font-semibold text-gray-900">{friendlyLabel}</span>
                      <span className="text-xs text-gray-400">
                        {new Date(event.event_timestamp).toLocaleString()}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span className="font-mono text-[11px] text-gray-600 bg-gray-50 px-1.5 py-0.5 rounded border border-gray-100">
                        {event.event_type}
                      </span>
                      <span>Category: {event.source_event_category}</span>
                      <span>Seq: #{event.sequence_number}</span>
                    </div>
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

