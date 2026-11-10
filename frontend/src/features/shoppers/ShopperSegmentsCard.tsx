import { useShopperSegments } from '../../hooks/queries';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';

interface ShopperSegmentsCardProps {
  merchantId: string;
  shopperId: string;
}

export function ShopperSegmentsCard({ merchantId, shopperId }: ShopperSegmentsCardProps) {
  const { data: segments, isLoading, isError, refetch } = useShopperSegments(merchantId, shopperId);

  if (isLoading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow min-h-[160px] flex items-center justify-center">
        <LoadingSpinner message="Loading segment memberships..." />
      </div>
    );
  }

  if (isError || !segments) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <ErrorMessage message="Failed to load segment memberships." retry={() => refetch()} />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-medium text-gray-900">Current Segment Membership</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Rule-based behavioural segments evaluated for this shopper
          </p>
        </div>
        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
          {segments.length} {segments.length === 1 ? 'Segment' : 'Segments'}
        </span>
      </div>

      <div className="p-6">
        {segments.length === 0 ? (
          <div className="text-center py-6 text-gray-500 text-sm">
            <svg
              className="w-10 h-10 text-gray-300 mx-auto mb-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
            This shopper does not currently qualify for any active behavioural segments.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {segments.map((m) => (
              <div
                key={m.segment_id}
                className="p-4 rounded-lg border border-purple-100 bg-purple-50/40 hover:bg-purple-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-600" />
                  <h4 className="text-sm font-bold text-gray-900">{m.segment_name}</h4>
                </div>
                <div className="mt-3 flex justify-between items-center text-[11px] text-gray-500">
                  <span className="font-mono text-gray-400">ID: {m.segment_id.slice(0, 8)}...</span>
                  <span>Evaluated: {new Date(m.generated_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

