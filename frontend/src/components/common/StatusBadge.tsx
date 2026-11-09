interface StatusBadgeProps {
  status: string;
  type?: 'health' | 'journey' | 'install' | 'general';
}

export function StatusBadge({ status, type = 'general' }: StatusBadgeProps) {
  const normalized = status.toUpperCase();

  let colorClasses = 'bg-gray-100 text-gray-800 border-gray-200';

  if (type === 'health' || normalized === 'HEALTHY' || normalized === 'NEEDS_ATTENTION' || normalized === 'AT_RISK') {
    switch (normalized) {
      case 'HEALTHY':
        colorClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200';
        break;
      case 'NEEDS_ATTENTION':
        colorClasses = 'bg-amber-50 text-amber-700 border-amber-200';
        break;
      case 'AT_RISK':
        colorClasses = 'bg-rose-50 text-rose-700 border-rose-200';
        break;
      default:
        colorClasses = 'bg-gray-100 text-gray-700 border-gray-200';
    }
  } else if (type === 'journey' || normalized === 'OPEN' || normalized === 'COMPLETED') {
    switch (normalized) {
      case 'OPEN':
        colorClasses = 'bg-blue-50 text-blue-700 border-blue-200';
        break;
      case 'COMPLETED':
        colorClasses = 'bg-purple-50 text-purple-700 border-purple-200';
        break;
      default:
        colorClasses = 'bg-gray-100 text-gray-700 border-gray-200';
    }
  } else if (type === 'install') {
    switch (normalized) {
      case 'INSTALLED':
        colorClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200';
        break;
      case 'UNINSTALLED':
        colorClasses = 'bg-gray-100 text-gray-600 border-gray-200';
        break;
      default:
        colorClasses = 'bg-amber-50 text-amber-700 border-amber-200';
    }
  }

  const label = status.replace(/_/g, ' ');

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colorClasses}`}
    >
      {label}
    </span>
  );
}

