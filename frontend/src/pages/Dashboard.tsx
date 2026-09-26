import { useMemo } from 'react';
import { PlatformSummary } from '../features/analytics/PlatformSummary';
import { PlatformTrend } from '../features/analytics/PlatformTrend';
import { FeatureMetrics } from '../features/analytics/FeatureMetrics';

export function Dashboard() {
  const { startDate, endDate } = useMemo(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    
    return {
      startDate: start.toISOString().split('T')[0],
      endDate: end.toISOString().split('T')[0]
    };
  }, []);

  return (
    <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Platform Overview</h1>
        <p className="mt-2 text-sm text-gray-600">
          Monitor core business metrics, feature adoption, and platform growth.
        </p>
      </div>

      <PlatformSummary />
      <PlatformTrend startDate={startDate} endDate={endDate} />
      <FeatureMetrics />
    </div>
  );
}
