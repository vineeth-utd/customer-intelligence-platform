import { useState } from 'react';
import { useMerchantHealth } from '../../hooks/queries';
import { StatusBadge } from '../../components/common/StatusBadge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import type { MerchantHealthResponse } from '../../types';
import { formatScore, parseNumericValue } from '../../utils';

interface MerchantHealthCardProps {
  merchantId: string;
  initialData?: MerchantHealthResponse | null;
}

export function MerchantHealthCard({ merchantId, initialData }: MerchantHealthCardProps) {
  const { data: fetchedData, isLoading, isError, refetch } = useMerchantHealth(
    initialData ? '' : merchantId
  );
  const data = initialData ?? fetchedData;

  const [expandedFactors, setExpandedFactors] = useState(false);

  if (isLoading && !data) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <LoadingSpinner message="Evaluating merchant health & risk..." />
      </div>
    );
  }

  if (isError && !data) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <ErrorMessage message="Failed to load merchant health data." retry={() => refetch()} />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white p-6 rounded-lg shadow text-center py-8">
        <p className="text-gray-500 text-sm">No health evaluation calculated for this merchant yet.</p>
      </div>
    );
  }

  const { contributing_factors } = data;
  const riskAlerts = contributing_factors?.risk_alerts || [];

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex flex-wrap justify-between items-center gap-2">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-medium text-gray-900">Merchant Health & Churn Risk</h3>
          <StatusBadge status={data.health_status} type="health" />
        </div>
        <span className="text-xs text-gray-400">
          Calculated {new Date(data.calculated_at).toLocaleString()}
        </span>
      </div>

      <div className="p-6">
        {/* Top KPI row */}
        {(() => {
          const healthNum = parseNumericValue(data.health_score) ?? 0;
          const churnNum = parseNumericValue(data.churn_risk_score) ?? 0;
          return (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">Health Score</div>
                <div className="mt-1 flex items-baseline">
                  <span className="text-3xl font-extrabold text-gray-900">{formatScore(data.health_score)}</span>
                  <span className="text-xs text-gray-500 ml-1">/ 100</span>
                </div>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full ${data.health_status === 'HEALTHY'
                      ? 'bg-emerald-500'
                      : data.health_status === 'NEEDS_ATTENTION'
                        ? 'bg-amber-500'
                        : 'bg-rose-500'
                      }`}
                    style={{ width: `${Math.min(100, Math.max(0, healthNum))}%` }}
                  />
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">Churn Risk</div>
                <div className="mt-1 flex items-baseline">
                  <span className="text-3xl font-bold text-gray-900">{formatScore(data.churn_risk_score)}</span>
                  <span className="text-xs text-gray-500 ml-1">/ 100</span>
                </div>
                <div className="mt-2 text-xs text-gray-500">
                  {churnNum > 60 ? 'Elevated churn risk' : churnNum > 30 ? 'Moderate risk' : 'Low risk'}
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">Feature Adoption</div>
                <div className="mt-1 text-2xl font-bold text-gray-900">{formatScore(data.feature_adoption_score)}</div>
                <div className="mt-2 text-xs text-gray-500">Entitled feature usage</div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">Platform Engagement</div>
                <div className="mt-1 text-2xl font-bold text-gray-900">{formatScore(data.engagement_score)}</div>
                <div className="mt-2 text-xs text-gray-500">Activity and session logins</div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">Business Performance</div>
                <div className="mt-1 text-2xl font-bold text-gray-900">{formatScore(data.business_performance_score)}</div>
                <div className="mt-2 text-xs text-gray-500">Order & revenue trajectory</div>
              </div>
            </div>
          );
        })()}

        {/* Risk Alerts */}
        {riskAlerts.length > 0 && (
          <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <h4 className="text-sm font-semibold text-amber-900">Deterministic Risk Alerts ({riskAlerts.length})</h4>
            </div>
            <ul className="list-disc list-inside space-y-1 text-xs text-amber-800 ml-1">
              {riskAlerts.map((alert, idx) => (
                <li key={idx}>{alert}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Explainable Contributing Factors Toggle */}
        <div className="border-t border-gray-100 pt-4">
          <button
            type="button"
            onClick={() => setExpandedFactors((prev) => !prev)}
            className="flex items-center justify-between w-full text-left text-sm font-medium text-indigo-600 hover:text-indigo-800 focus:outline-none"
          >
            <span>Explainable Contributing Factor Breakdown</span>
            <span>{expandedFactors ? '▲ Hide breakdown' : '▼ View score details'}</span>
          </button>

          {expandedFactors && (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <h5 className="font-semibold text-gray-800 mb-2">Feature Adoption Factors</h5>
                <pre className="bg-white p-2 rounded border border-gray-200 overflow-x-auto text-[11px] text-gray-700">
                  {JSON.stringify(contributing_factors?.feature_adoption ?? {}, null, 2)}
                </pre>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <h5 className="font-semibold text-gray-800 mb-2">Engagement Factors</h5>
                <pre className="bg-white p-2 rounded border border-gray-200 overflow-x-auto text-[11px] text-gray-700">
                  {JSON.stringify(contributing_factors?.engagement ?? {}, null, 2)}
                </pre>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <h5 className="font-semibold text-gray-800 mb-2">Business Performance Factors</h5>
                <pre className="bg-white p-2 rounded border border-gray-200 overflow-x-auto text-[11px] text-gray-700">
                  {JSON.stringify(contributing_factors?.business_performance ?? {}, null, 2)}
                </pre>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <h5 className="font-semibold text-gray-800 mb-2">Subscription Lifecycle Factors</h5>
                <pre className="bg-white p-2 rounded border border-gray-200 overflow-x-auto text-[11px] text-gray-700">
                  {JSON.stringify(contributing_factors?.subscription ?? {}, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

