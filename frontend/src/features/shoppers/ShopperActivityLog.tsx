import { useState, useMemo } from 'react';
import { useShopperActivity } from '../../hooks/queries';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { Pagination } from '../../components/common/Pagination';
import { DateRangePicker } from '../../components/common/DateRangePicker';

interface ShopperActivityLogProps {
  merchantId: string;
  shopperId: string;
}

export function ShopperActivityLog({ merchantId, shopperId }: ShopperActivityLogProps) {
  const initialDates = useMemo(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    return {
      startDate: start.toISOString().split('T')[0],
      endDate: end.toISOString().split('T')[0],
    };
  }, []);

  const [dateRange, setDateRange] = useState<{ startDate?: string; endDate?: string }>(initialDates);
  const [isAllTime, setIsAllTime] = useState(false);
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const handleDateChange = (newRange: { startDate: string; endDate: string }) => {
    setIsAllTime(false);
    setDateRange(newRange);
    setOffset(0); // Reset pagination on date filter change
  };

  const handleToggleAllTime = () => {
    if (isAllTime) {
      setIsAllTime(false);
      setDateRange(initialDates);
    } else {
      setIsAllTime(true);
      setDateRange({});
    }
    setOffset(0); // Reset pagination on date filter change
  };

  const effectiveStart = isAllTime ? undefined : dateRange.startDate;
  const effectiveEnd = isAllTime ? undefined : dateRange.endDate;

  const { data, isLoading, isError, refetch } = useShopperActivity(
    merchantId,
    shopperId,
    limit,
    offset,
    effectiveStart,
    effectiveEnd
  );

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden flex flex-col h-full">
      {/* Header and Filter Controls */}
      <div className="px-6 py-5 border-b border-gray-200 flex flex-wrap justify-between items-center gap-4">
        <div>
          <h3 className="text-lg font-medium text-gray-900">Storefront Activity Log</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Paginated raw and curated event stream for investigation drill-downs
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleToggleAllTime}
            className={`text-xs px-3 py-1.5 rounded font-medium border transition-colors ${
              isAllTime
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {isAllTime ? '✓ All Time Selected' : 'Show All Time'}
          </button>

          {!isAllTime && (
            <DateRangePicker
              startDate={dateRange.startDate || initialDates.startDate}
              endDate={dateRange.endDate || initialDates.endDate}
              onChange={handleDateChange}
            />
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <div className="p-12 flex items-center justify-center min-h-[350px]">
          <LoadingSpinner message="Loading storefront activity stream..." />
        </div>
      ) : isError || !data ? (
        <div className="p-6">
          <ErrorMessage message="Failed to load activity events." retry={() => refetch()} />
        </div>
      ) : data.items.length === 0 ? (
        <div className="p-12 text-center">
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
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h4 className="text-base font-medium text-gray-900">No Activity Events Found</h4>
          <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
            {isAllTime
              ? 'No storefront events have been recorded for this shopper.'
              : 'No activity events match the selected date window. Try selecting "Show All Time" or extending the date range.'}
          </p>
        </div>
      ) : (
        <>
          <div className="px-6 py-3 bg-gray-50 border-b border-gray-100 flex justify-between items-center text-xs text-gray-500">
            <span>
              Showing {data.items.length} events (Page {Math.floor(offset / limit) + 1} of{' '}
              {Math.max(1, Math.ceil(data.total / limit))})
            </span>
            <span>
              Total Events: <strong className="text-gray-900">{data.total}</strong>
            </span>
          </div>

          <div className="overflow-x-auto flex-1">
            <table className="min-w-full divide-y divide-gray-200 text-xs">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
                    Timestamp
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
                    Event Type
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
                    Session & Source
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
                    Activity Details
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.items.map((event) => {
                  const details = Object.entries(event.activity_details || {});

                  return (
                    <tr key={event.event_id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-3.5 whitespace-nowrap text-gray-600 font-medium">
                        {new Date(event.event_timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-3.5 whitespace-nowrap">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono">
                          {event.event_type}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 whitespace-nowrap text-gray-500 font-mono text-[11px]">
                        <div>Session: {event.session_id.slice(0, 8)}...</div>
                        <div className="text-gray-400">Src: {event.source}</div>
                      </td>
                      <td className="px-6 py-3.5 text-gray-700">
                        {details.length === 0 ? (
                          <span className="text-gray-400 italic">No details</span>
                        ) : (
                          <div className="flex flex-wrap gap-1.5 max-w-xl">
                            {details.map(([k, v]) => (
                              <span
                                key={k}
                                className="inline-flex items-center px-2 py-0.5 rounded bg-gray-100 text-gray-700 border border-gray-200 text-[11px]"
                              >
                                <span className="font-semibold text-gray-500 mr-1">{k}:</span>
                                <span className="font-mono text-gray-900 truncate max-w-xs">
                                  {typeof v === 'object' && v !== null
                                    ? JSON.stringify(v)
                                    : String(v)}
                                </span>
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <Pagination total={data.total} limit={limit} offset={offset} onPageChange={setOffset} />
        </>
      )}
    </div>
  );
}
