import { useState } from 'react';

interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onChange: (range: { startDate: string; endDate: string }) => void;
}

export function DateRangePicker({ startDate, endDate, onChange }: DateRangePickerProps) {
  const [selectedPreset, setSelectedPreset] = useState<'7d' | '30d' | '90d' | 'custom'>('30d');

  const applyPreset = (days: number, preset: '7d' | '30d' | '90d') => {
    setSelectedPreset(preset);
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    onChange({
      startDate: start.toISOString().split('T')[0],
      endDate: end.toISOString().split('T')[0],
    });
  };

  return (
    <div className="flex flex-wrap items-center gap-2 bg-white px-3 py-2 rounded-lg shadow-sm border border-gray-200 text-sm">
      <span className="text-gray-500 font-medium mr-1">Time Period:</span>
      <div className="inline-flex rounded-md shadow-sm" role="group">
        <button
          type="button"
          onClick={() => applyPreset(7, '7d')}
          className={`px-3 py-1 text-xs font-medium rounded-l-md border ${
            selectedPreset === '7d'
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          }`}
        >
          7D
        </button>
        <button
          type="button"
          onClick={() => applyPreset(30, '30d')}
          className={`px-3 py-1 text-xs font-medium border-t border-b ${
            selectedPreset === '30d'
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          }`}
        >
          30D
        </button>
        <button
          type="button"
          onClick={() => applyPreset(90, '90d')}
          className={`px-3 py-1 text-xs font-medium rounded-r-md border ${
            selectedPreset === '90d'
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          }`}
        >
          90D
        </button>
      </div>

      <div className="flex items-center gap-1.5 ml-2">
        <input
          type="date"
          value={startDate}
          max={endDate}
          onChange={(e) => {
            setSelectedPreset('custom');
            onChange({ startDate: e.target.value, endDate });
          }}
          className="border border-gray-300 rounded px-2 py-0.5 text-xs text-gray-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        <span className="text-gray-400">to</span>
        <input
          type="date"
          value={endDate}
          min={startDate}
          onChange={(e) => {
            setSelectedPreset('custom');
            onChange({ startDate, endDate: e.target.value });
          }}
          className="border border-gray-300 rounded px-2 py-0.5 text-xs text-gray-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>
    </div>
  );
}

