import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  useCampaign,
  useCampaignPerformance,
  useCampaignAttribution,
  useCampaignJourneyCorrelation,
  useCampaignAudience,
} from '../../hooks/queries/useCampaignQueries';
import { useMerchant } from '../../hooks/queries/useMerchantQueries';
import { DateRangePicker } from '../../components/common/DateRangePicker';
import { StatusBadge } from '../../components/common/StatusBadge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';

import { CampaignPerformanceCard } from './CampaignPerformanceCard';
import { CampaignAttributionCard } from './CampaignAttributionCard';
import { CampaignJourneyCorrelationCard } from './CampaignJourneyCorrelationCard';
import { CampaignAudienceCard } from './CampaignAudienceCard';

type CampaignTabKey = 'performance' | 'attribution' | 'journey' | 'audience';

interface CampaignOverviewProps {
  merchantId: string;
  campaignId: string;
}

export function CampaignOverview({ merchantId, campaignId }: CampaignOverviewProps) {
  const initialDates = useMemo(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    return {
      startDate: start.toISOString().split('T')[0],
      endDate: end.toISOString().split('T')[0],
    };
  }, []);

  const [dateRange, setDateRange] = useState(initialDates);
  const [activeTab, setActiveTab] = useState<CampaignTabKey>('performance');

  const {
    data: campaign,
    isLoading: loadingCampaign,
    isError: errorCampaign,
    error: campaignError,
    refetch: refetchCampaign,
  } = useCampaign(merchantId, campaignId);

  const { data: merchant } = useMerchant(merchantId);

  // Queries for each tab driven by the date range
  const {
    data: performanceData,
    isLoading: loadingPerformance,
    isError: errorPerformance,
    refetch: refetchPerformance,
  } = useCampaignPerformance(
    merchantId,
    campaignId,
    dateRange.startDate,
    dateRange.endDate
  );

  const {
    data: attributionData,
    isLoading: loadingAttribution,
    isError: errorAttribution,
    refetch: refetchAttribution,
  } = useCampaignAttribution(
    merchantId,
    campaignId,
    dateRange.startDate,
    dateRange.endDate
  );

  const {
    data: correlationData,
    isLoading: loadingCorrelation,
    isError: errorCorrelation,
    refetch: refetchCorrelation,
  } = useCampaignJourneyCorrelation(
    merchantId,
    campaignId,
    dateRange.startDate,
    dateRange.endDate
  );

  const {
    data: audienceData,
    isLoading: loadingAudience,
    isError: errorAudience,
    refetch: refetchAudience,
  } = useCampaignAudience(merchantId, campaignId);

  if (loadingCampaign) {
    return (
      <div className="bg-white p-12 rounded-lg shadow flex items-center justify-center min-h-[400px]">
        <LoadingSpinner message="Loading campaign intelligence..." />
      </div>
    );
  }

  if (errorCampaign || !campaign) {
    const message =
      campaignError instanceof Error ? campaignError.message : 'Failed to load campaign details.';
    return (
      <div className="bg-white p-8 rounded-lg shadow">
        <ErrorMessage message={message} retry={() => refetchCampaign()} />
      </div>
    );
  }

  const tabs: { key: CampaignTabKey; label: string; badge?: string }[] = [
    { key: 'performance', label: 'Performance' },
    { key: 'attribution', label: 'Attribution' },
    { key: 'journey', label: 'Journey Impact' },
    { key: 'audience', label: 'Audience', badge: 'Current Segments' },
  ];

  const formatLifetime = () => {
    if (!campaign.start_at) return 'Not scheduled';
    const start = new Date(campaign.start_at).toLocaleDateString();
    if (!campaign.end_at) return `Started ${start} (Active / Ongoing)`;
    const end = new Date(campaign.end_at).toLocaleDateString();
    return `${start} – ${end}`;
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation Bar */}
      <nav className="flex items-center text-xs text-gray-500 gap-2 mb-2">
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
        <span>&rsaquo;</span>
        <span className="text-gray-400">Campaigns</span>
        <span>&rsaquo;</span>
        <span className="font-semibold text-gray-900 truncate max-w-xs">
          {campaign.campaign_name}
        </span>
      </nav>

      {/* Persistent Campaign Header Bar */}
      <div className="bg-white p-6 rounded-lg shadow border-l-4 border-indigo-600 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-2xl font-bold text-gray-900">{campaign.campaign_name}</h2>
            <StatusBadge status={campaign.status} type="campaign" />
            <span className="text-xs font-medium bg-gray-100 text-gray-700 px-2 py-0.5 rounded capitalize">
              {campaign.campaign_type} • {campaign.campaign_medium}
            </span>
            {campaign.target_segment_name && (
              <span className="text-xs font-medium bg-indigo-50 text-indigo-700 px-2.5 py-0.5 rounded-full border border-indigo-200">
                Target: {campaign.target_segment_name}
              </span>
            )}
          </div>

          <p className="text-xs text-gray-500 mt-2 flex flex-wrap gap-x-5 gap-y-1">
            <span>
              Lifetime: <strong className="text-gray-700">{formatLifetime()}</strong>
            </span>
            <span>
              Campaign ID: <strong className="font-mono text-gray-700">{campaign.campaign_id}</strong>
            </span>
          </p>
        </div>

        <div>
          <div className="text-right text-[11px] text-gray-400 mb-1">Analytical Horizon:</div>
          <DateRangePicker
            startDate={dateRange.startDate}
            endDate={dateRange.endDate}
            onChange={setDateRange}
          />
        </div>
      </div>

      {/* Campaign Intelligence Tab Navigation */}
      <div className="border-b border-gray-200 bg-white px-4 rounded-t-lg shadow-xs">
        <nav className="-mb-px flex space-x-6 overflow-x-auto" aria-label="Campaign Tabs">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors focus:outline-none ${
                  isActive
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span>{tab.label}</span>
                {tab.badge && (
                  <span className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded font-medium">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab 1: Performance */}
      {activeTab === 'performance' && (
        <div>
          {loadingPerformance ? (
            <div className="bg-white p-12 rounded-lg shadow flex items-center justify-center min-h-[350px]">
              <LoadingSpinner message="Loading campaign performance..." />
            </div>
          ) : errorPerformance || !performanceData ? (
            <div className="bg-white p-8 rounded-lg shadow">
              <ErrorMessage
                message="Failed to load performance metrics."
                retry={() => refetchPerformance()}
              />
            </div>
          ) : (
            <CampaignPerformanceCard performance={performanceData} />
          )}
        </div>
      )}

      {/* Tab 2: Attribution */}
      {activeTab === 'attribution' && (
        <div>
          {loadingAttribution ? (
            <div className="bg-white p-12 rounded-lg shadow flex items-center justify-center min-h-[350px]">
              <LoadingSpinner message="Loading multi-perspective attribution..." />
            </div>
          ) : errorAttribution || !attributionData ? (
            <div className="bg-white p-8 rounded-lg shadow">
              <ErrorMessage
                message="Failed to load attribution metrics."
                retry={() => refetchAttribution()}
              />
            </div>
          ) : (
            <CampaignAttributionCard attribution={attributionData} />
          )}
        </div>
      )}

      {/* Tab 3: Journey Impact */}
      {activeTab === 'journey' && (
        <div>
          {loadingCorrelation ? (
            <div className="bg-white p-12 rounded-lg shadow flex items-center justify-center min-h-[350px]">
              <LoadingSpinner message="Loading journey impact analysis..." />
            </div>
          ) : errorCorrelation || !correlationData ? (
            <div className="bg-white p-8 rounded-lg shadow">
              <ErrorMessage
                message="Failed to load journey correlation data."
                retry={() => refetchCorrelation()}
              />
            </div>
          ) : (
            <CampaignJourneyCorrelationCard correlation={correlationData} />
          )}
        </div>
      )}

      {/* Tab 4: Audience (Current Segment Response) */}
      {activeTab === 'audience' && (
        <div>
          {loadingAudience ? (
            <div className="bg-white p-12 rounded-lg shadow flex items-center justify-center min-h-[350px]">
              <LoadingSpinner message="Loading audience response..." />
            </div>
          ) : errorAudience || !audienceData ? (
            <div className="bg-white p-8 rounded-lg shadow">
              <ErrorMessage
                message="Failed to load audience analysis."
                retry={() => refetchAudience()}
              />
            </div>
          ) : (
            <CampaignAudienceCard audience={audienceData} />
          )}
        </div>
      )}
    </div>
  );
}

