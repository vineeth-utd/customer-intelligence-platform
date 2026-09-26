import { useMerchants } from '../../hooks/queries';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';

interface MerchantSelectorProps {
  selectedMerchantId: string | null;
  onSelect: (merchantId: string) => void;
}

export function MerchantSelector({ selectedMerchantId, onSelect }: MerchantSelectorProps) {
  const { data, isLoading, isError, refetch } = useMerchants(50, 0);

  if (isLoading) {
    return <div className="py-2"><LoadingSpinner message="Loading merchants..." /></div>;
  }

  if (isError || !data) {
    return <ErrorMessage message="Failed to load merchants." retry={() => refetch()} />;
  }

  if (data.items.length === 0) {
    return <p className="text-sm text-gray-500 py-2">No merchants found.</p>;
  }

  return (
    <div className="w-full max-w-md">
      <label htmlFor="merchant-select" className="block text-sm font-medium text-gray-700 mb-1">
        Select Merchant
      </label>
      <select
        id="merchant-select"
        className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md shadow-sm border bg-white"
        value={selectedMerchantId || ''}
        onChange={(e) => onSelect(e.target.value)}
      >
        <option value="" disabled>-- Select a Merchant --</option>
        {data.items.map((merchant) => (
          <option key={merchant.merchant_id} value={merchant.merchant_id}>
            {merchant.merchant_name} ({merchant.shopify_store_id})
          </option>
        ))}
      </select>
    </div>
  );
}
