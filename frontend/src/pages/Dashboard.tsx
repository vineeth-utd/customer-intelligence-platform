import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context';
import { usePlatformDashboard } from '../hooks/queries';
import { DateRangePicker } from '../components/common/DateRangePicker';
import { PlatformSummary } from '../features/analytics/PlatformSummary';
import { PlatformTrend } from '../features/analytics/PlatformTrend';
import { FeatureMetrics } from '../features/analytics/FeatureMetrics';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';

export function Dashboard() {
  const navigate = useNavigate();
  const { isMerchant, merchantId } = useAuth();

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

  const { data, isLoading, isError, error, refetch } = usePlatformDashboard(
    dateRange.startDate,
    dateRange.endDate,
    !isMerchant
  );

  // If a MERCHANT principal lands on Platform dashboard, redirect or show barrier
  if (isMerchant && merchantId) {
    return (
      <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-8 text-center max-w-lg mx-auto my-12">
          <h3 className="text-lg font-bold text-amber-900">Platform Overview Restricted</h3>
          <p className="mt-2 text-sm text-amber-700">
            You are authenticated with a Store Principal (MERCHANT) scope. Platform-level overview is restricted to internal operations.
          </p>
          <button
            onClick={() => navigate(`/merchants/${merchantId}`)}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
          >
            Go to My Store Intelligence
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Platform Overview</h1>
          <p className="mt-2 text-sm text-gray-600">
            Consolidated platform-wide intelligence, growth trends, and feature adoption.
          </p>
        </div>

        <DateRangePicker
          startDate={dateRange.startDate}
          endDate={dateRange.endDate}
          onChange={setDateRange}
        />
      </div>

      {isLoading ? (
        <div className="bg-white p-12 rounded-lg shadow flex items-center justify-center min-h-[350px]">
          <LoadingSpinner message="Loading consolidated platform overview..." />
        </div>
      ) : isError || !data ? (
        <div className="bg-white p-8 rounded-lg shadow">
          <ErrorMessage
            message={error instanceof Error ? error.message : 'Failed to load platform dashboard.'}
            retry={() => refetch()}
          />
        </div>
      ) : (
        <>
          <PlatformSummary summary={data.summary} />
          <PlatformTrend
            startDate={dateRange.startDate}
            endDate={dateRange.endDate}
            trends={data.trends}
          />
          <FeatureMetrics features={data.features} />
        </>
      )}
    </div>
  );
}
