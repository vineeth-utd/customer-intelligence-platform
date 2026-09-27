import { useState } from 'react';
import { MerchantSelector } from '../features/merchants/MerchantSelector';
import { MerchantOverview } from '../features/merchants/MerchantOverview';

export function Merchants() {
  const [selectedMerchantId, setSelectedMerchantId] = useState<string | null>(null);

  return (
    <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Merchants</h1>
        <p className="mt-2 text-sm text-gray-600">
          Investigate performance and details for specific merchants.
        </p>
      </div>

      <div className="mb-8">
        <MerchantSelector 
          selectedMerchantId={selectedMerchantId} 
          onSelect={setSelectedMerchantId} 
        />
      </div>

      {selectedMerchantId ? (
        <MerchantOverview merchantId={selectedMerchantId} key={selectedMerchantId} />
      ) : (
        <div className="bg-white p-12 rounded-lg shadow flex flex-col items-center justify-center text-center">
          <svg className="w-12 h-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900">No Merchant Selected</h3>
          <p className="mt-1 text-sm text-gray-500">Select a merchant from the list above to view their performance overview.</p>
        </div>
      )}
    </div>
  );
}
