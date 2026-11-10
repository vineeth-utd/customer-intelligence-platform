import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context';
import { authApi } from '../../api/auth';
import type { DevMerchantOption } from '../../types';

interface DevAuthModalProps {
  isOpen: boolean;
  onClose?: () => void;
  canDismiss?: boolean;
}

export function DevAuthModal({ isOpen, onClose, canDismiss = true }: DevAuthModalProps) {
  const navigate = useNavigate();
  const { loginWithDevPrincipal, setManualToken } = useAuth();
  const [merchants, setMerchants] = useState<DevMerchantOption[]>([]);
  const [selectedMerchantId, setSelectedMerchantId] = useState<string>('');
  const [customToken, setCustomToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      authApi
        .getDevPrincipals()
        .then((res) => {
          setMerchants(res.merchants || []);
          if (res.merchants && res.merchants.length > 0) {
            setSelectedMerchantId(res.merchants[0].merchant_id);
          }
        })
        .catch(() => {
          // In case dev endpoint isn't accessible or DB is empty
        });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSelectInternal = async () => {
    setLoading(true);
    setError(null);
    try {
      await loginWithDevPrincipal({ scope: 'INTERNAL' });
      onClose?.();
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to obtain INTERNAL token');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectMerchant = async () => {
    if (!selectedMerchantId) {
      setError('Please select a merchant store');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await loginWithDevPrincipal({
        scope: 'MERCHANT',
        merchant_id: selectedMerchantId,
      });
      onClose?.();
      navigate(`/merchants/${selectedMerchantId}`, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to obtain MERCHANT token');
    } finally {
      setLoading(false);
    }
  };

  const handleApplyCustomToken = () => {
    if (!customToken.trim()) {
      setError('Please enter a valid Bearer token');
      return;
    }
    try {
      setManualToken(customToken.trim());
      onClose?.();
      try {
        const parts = customToken.trim().split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
          if (payload.scope === 'MERCHANT' && payload.merchant_id) {
            navigate(`/merchants/${payload.merchant_id}`, { replace: true });
            return;
          }
        }
      } catch {
        // Fallback to home
      }
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid token format');
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6 relative">
        {canDismiss && onClose && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 focus:outline-none"
          >
            <span className="sr-only">Close</span>
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}

        <div className="text-center mb-5">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-indigo-100 text-indigo-600 mb-3">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
              />
            </svg>
          </div>
          <h3 className="text-xl font-bold text-gray-900">Development Identity Selector</h3>
          <p className="mt-1 text-sm text-gray-500">
            Select a principal to sign in for this local development session.
          </p>
        </div>

        {/* Development Environment Callout */}
        <div className="mb-5 p-3 bg-amber-50/80 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-start gap-2.5">
          <span className="text-base leading-none mt-0.5">⚠️</span>
          <div>
            <strong className="font-semibold text-amber-900">Development Tooling Only:</strong>
            <p className="mt-0.5 text-amber-700 leading-relaxed">
              This identity selector is backed by local mock token endpoints registered only when{' '}
              <code className="bg-amber-100 px-1 py-0.2 rounded font-mono text-[11px] text-amber-900">
                settings.environment == &apos;development&apos;
              </code>
              . These endpoints return 404 in staging and production environments.
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div className="p-4 border border-gray-200 rounded-lg hover:border-indigo-500 transition-colors">
            <h4 className="font-semibold text-gray-900 flex items-center justify-between">
              <span>Platform Admin (INTERNAL)</span>
              <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-mono">INTERNAL</span>
            </h4>
            <p className="text-xs text-gray-500 mt-1 mb-3">
              Full access to platform dashboard, cross-merchant metrics, and all merchant drill-downs.
            </p>
            <button
              onClick={handleSelectInternal}
              disabled={loading}
              className="w-full py-2 px-4 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {loading ? 'Authenticating...' : 'Sign In as Internal Admin'}
            </button>
          </div>

          <div className="p-4 border border-gray-200 rounded-lg hover:border-indigo-500 transition-colors">
            <h4 className="font-semibold text-gray-900 flex items-center justify-between">
              <span>Store Principal (MERCHANT)</span>
              <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded font-mono">MERCHANT</span>
            </h4>
            <p className="text-xs text-gray-500 mt-1 mb-3">
              Scoped to a single merchant. Platform-wide overview is hidden and cross-tenant access is forbidden.
            </p>
            {merchants.length > 0 ? (
              <div className="space-y-3">
                <select
                  value={selectedMerchantId}
                  onChange={(e) => setSelectedMerchantId(e.target.value)}
                  className="w-full border border-gray-300 rounded-md p-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {merchants.map((m) => (
                    <option key={m.merchant_id} value={m.merchant_id}>
                      {m.merchant_name} ({m.shopify_store_id})
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleSelectMerchant}
                  disabled={loading || !selectedMerchantId}
                  className="w-full py-2 px-4 bg-emerald-600 text-white rounded-md text-sm font-medium hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50"
                >
                  {loading ? 'Authenticating...' : 'Sign In as Selected Merchant'}
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <input
                  type="text"
                  placeholder="Enter Merchant UUID"
                  value={selectedMerchantId}
                  onChange={(e) => setSelectedMerchantId(e.target.value)}
                  className="w-full border border-gray-300 rounded-md p-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                />
                <button
                  onClick={handleSelectMerchant}
                  disabled={loading || !selectedMerchantId}
                  className="w-full py-2 px-4 bg-emerald-600 text-white rounded-md text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
                >
                  {loading ? 'Authenticating...' : 'Sign In as Merchant'}
                </button>
              </div>
            )}
          </div>

          <details className="text-xs text-gray-500 pt-2">
            <summary className="cursor-pointer font-medium hover:text-gray-700">
              Paste Custom Bearer Token
            </summary>
            <div className="mt-2 space-y-2">
              <textarea
                rows={2}
                value={customToken}
                onChange={(e) => setCustomToken(e.target.value)}
                placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                className="w-full border border-gray-300 rounded-md p-2 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <button
                onClick={handleApplyCustomToken}
                className="w-full py-1.5 px-3 bg-gray-800 text-white rounded text-xs font-medium hover:bg-gray-900"
              >
                Apply Token
              </button>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}
