import type { CampaignAudienceAnalysisResult } from '../../types';
import { formatPercent } from '../../utils';

interface CampaignAudienceCardProps {
  audience: CampaignAudienceAnalysisResult;
}

export function CampaignAudienceCard({ audience }: CampaignAudienceCardProps) {
  const {
    target_segment_name,
    target_segment_current_members,
    unique_shoppers_reached,
    unique_shoppers_engaged,
    unique_shoppers_converted,
    target_segment_current_members_reached,
    target_segment_current_members_engaged,
    target_segment_current_members_converted,
    non_target_current_shoppers_reached,
    non_target_current_shoppers_engaged,
    non_target_current_shoppers_converted,
    current_segments_breakdown,
  } = audience;

  const targetConvRate =
    target_segment_current_members_reached > 0
      ? (target_segment_current_members_converted / target_segment_current_members_reached) * 100
      : 0;

  const nonTargetConvRate =
    non_target_current_shoppers_reached > 0
      ? (non_target_current_shoppers_converted / non_target_current_shoppers_reached) * 100
      : 0;

  const overallConvRate =
    unique_shoppers_reached > 0
      ? (unique_shoppers_converted / unique_shoppers_reached) * 100
      : 0;

  return (
    <div className="space-y-6">
      {/* Explanatory Callout regarding Current vs Historical Membership */}
      <div className="bg-amber-50/70 border-l-4 border-amber-500 p-4 rounded-r-lg">
        <div className="flex items-start">
          <div className="flex-shrink-0 text-amber-600">
            <svg className="w-5 h-5 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <div className="ml-3 text-xs text-amber-900 leading-relaxed">
            <span className="font-bold">Current Segment Response:</span> Segments are evaluated based on shoppers&apos; <strong>current segment membership</strong>. Because shoppers dynamically enter and exit segments as their store activity evolves, this analysis demonstrates how current segment cohorts responded to this campaign; it does not indicate or imply historical membership at the moment of campaign dispatch.
          </div>
        </div>
      </div>

      {/* Target vs Non-Target Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Target Segment Card */}
        <div className="bg-white p-6 rounded-lg shadow border-t-4 border-indigo-600">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
              Target Audience
            </span>
            <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-medium">
              Intended
            </span>
          </div>
          <h4 className="text-lg font-bold text-gray-900 mt-1">{target_segment_name}</h4>
          <p className="text-xs text-gray-500 mt-0.5">
            Current Pool: {target_segment_current_members.toLocaleString()} members
          </p>

          <div className="mt-4 pt-4 border-t border-gray-100 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-500">Current Members Reached</span>
              <span className="font-semibold text-gray-900">
                {target_segment_current_members_reached.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Current Members Engaged</span>
              <span className="font-semibold text-gray-900">
                {target_segment_current_members_engaged.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Current Members Converted</span>
              <span className="font-semibold text-emerald-600">
                {target_segment_current_members_converted.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between pt-1 border-t border-gray-50 font-bold">
              <span className="text-gray-700">Conversion Rate</span>
              <span className="text-indigo-600">{targetConvRate.toFixed(1)}%</span>
            </div>
          </div>
        </div>

        {/* Non-Target / Spillover Card */}
        <div className="bg-white p-6 rounded-lg shadow border-t-4 border-slate-400">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Non-Target Current Shoppers
            </span>
            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded font-medium">
              Spillover / Shift
            </span>
          </div>
          <h4 className="text-lg font-bold text-gray-900 mt-1">Outside Target Segment</h4>
          <p className="text-xs text-gray-500 mt-0.5">Shoppers outside target definition today</p>

          <div className="mt-4 pt-4 border-t border-gray-100 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-500">Non-Target Reached</span>
              <span className="font-semibold text-gray-900">
                {non_target_current_shoppers_reached.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Non-Target Engaged</span>
              <span className="font-semibold text-gray-900">
                {non_target_current_shoppers_engaged.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Non-Target Converted</span>
              <span className="font-semibold text-emerald-600">
                {non_target_current_shoppers_converted.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between pt-1 border-t border-gray-50 font-bold">
              <span className="text-gray-700">Conversion Rate</span>
              <span className="text-slate-700">{nonTargetConvRate.toFixed(1)}%</span>
            </div>
          </div>
        </div>

        {/* Overall Reach Card */}
        <div className="bg-white p-6 rounded-lg shadow border-t-4 border-emerald-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-600">
              Total Audience Response
            </span>
            <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded font-medium">
              Net Reach
            </span>
          </div>
          <h4 className="text-lg font-bold text-gray-900 mt-1">All Shoppers Reached</h4>
          <p className="text-xs text-gray-500 mt-0.5">Deduplicated unique customer impact</p>

          <div className="mt-4 pt-4 border-t border-gray-100 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-500">Unique Shoppers Reached</span>
              <span className="font-semibold text-gray-900">
                {unique_shoppers_reached.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Unique Shoppers Engaged</span>
              <span className="font-semibold text-gray-900">
                {unique_shoppers_engaged.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Unique Shoppers Converted</span>
              <span className="font-semibold text-emerald-600">
                {unique_shoppers_converted.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between pt-1 border-t border-gray-50 font-bold">
              <span className="text-gray-700">Net Conversion Rate</span>
              <span className="text-emerald-600">{overallConvRate.toFixed(1)}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Breakdown by Current Segments Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h4 className="text-sm font-semibold text-gray-900">
            Response Across Current Segments
          </h4>
          <p className="text-xs text-gray-500 mt-0.5">
            Engagement and conversion rates categorized by shoppers&apos; active segment status today
          </p>
        </div>

        {current_segments_breakdown && current_segments_breakdown.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-xs">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
                    Segment
                  </th>
                  <th className="px-6 py-3 text-right font-medium text-gray-500 uppercase tracking-wider">
                    Current Members
                  </th>
                  <th className="px-6 py-3 text-right font-medium text-gray-500 uppercase tracking-wider">
                    Reached
                  </th>
                  <th className="px-6 py-3 text-right font-medium text-gray-500 uppercase tracking-wider">
                    Engaged
                  </th>
                  <th className="px-6 py-3 text-right font-medium text-gray-500 uppercase tracking-wider">
                    Converted
                  </th>
                  <th className="px-6 py-3 text-right font-medium text-gray-500 uppercase tracking-wider">
                    Conversion Rate
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {current_segments_breakdown.map((seg) => {
                  const isTarget = seg.segment_name === target_segment_name;
                  return (
                    <tr key={seg.segment_id} className={isTarget ? 'bg-indigo-50/30' : 'hover:bg-gray-50'}>
                      <td className="px-6 py-3 whitespace-nowrap font-medium text-gray-900 flex items-center gap-2">
                        <span>{seg.segment_name}</span>
                        {isTarget && (
                          <span className="text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.2 rounded font-semibold">
                            Target
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-3 whitespace-nowrap text-right text-gray-600">
                        {seg.current_members_count.toLocaleString()}
                      </td>
                      <td className="px-6 py-3 whitespace-nowrap text-right text-gray-900">
                        {seg.reached_shoppers_count.toLocaleString()}
                      </td>
                      <td className="px-6 py-3 whitespace-nowrap text-right text-gray-900">
                        {seg.engaged_shoppers_count.toLocaleString()}
                      </td>
                      <td className="px-6 py-3 whitespace-nowrap text-right text-emerald-600 font-semibold">
                        {seg.converted_shoppers_count.toLocaleString()}
                      </td>
                      <td className="px-6 py-3 whitespace-nowrap text-right font-bold text-gray-900">
                        {formatPercent(seg.conversion_rate, 1)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-gray-400 text-xs">
            No segment response breakdown available for this campaign.
          </div>
        )}
      </div>
    </div>
  );
}

