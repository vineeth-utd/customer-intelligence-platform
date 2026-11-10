import { useState } from 'react';
import { Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context';
import { DevAuthModal } from './components/common/DevAuthModal';
import { Dashboard } from './pages/Dashboard';
import { Merchants } from './pages/Merchants';
import { ShopperIntelligence } from './pages/ShopperIntelligence';

function Navigation() {
  const location = useLocation();
  const { isAuthenticated, isInternal, isMerchant, principal, merchantId, logout } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <span className="text-xl font-black text-indigo-600 tracking-tight">CIP</span>
                <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                  MVP 4.5
                </span>
              </div>

              {isAuthenticated && (
                <div className="hidden sm:-my-px sm:ml-8 sm:flex sm:space-x-8">
                  {isInternal && (
                    <>
                      <Link
                        to="/"
                        className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                          location.pathname === '/'
                            ? 'border-indigo-500 text-gray-900'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        Platform Overview
                      </Link>
                      <Link
                        to="/merchants"
                        className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                          location.pathname.startsWith('/merchants')
                            ? 'border-indigo-500 text-gray-900'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        Merchants
                      </Link>
                    </>
                  )}

                  {isMerchant && merchantId && (
                    <Link
                      to={`/merchants/${merchantId}`}
                      className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        location.pathname.startsWith('/merchants')
                          ? 'border-indigo-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      Store Intelligence
                    </Link>
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center gap-3">
              {isAuthenticated && principal ? (
                <div className="flex items-center gap-3">
                  <div className="hidden md:flex flex-col text-right">
                    <span className="text-xs font-medium text-gray-900">
                      {principal.email || principal.user_id}
                    </span>
                    <span className="text-[10px] text-gray-500 font-mono">
                      {isInternal ? 'INTERNAL (Admin)' : `MERCHANT: ${merchantId?.slice(0, 8)}...`}
                    </span>
                  </div>

                  <span
                    className={`text-xs px-2 py-0.5 rounded font-mono font-semibold ${
                      isInternal
                        ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                        : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    }`}
                  >
                    {principal.scope}
                  </span>

                  <button
                    type="button"
                    onClick={() => setModalOpen(true)}
                    className="text-xs text-gray-600 hover:text-gray-900 font-medium px-2.5 py-1 rounded border border-gray-300 hover:bg-gray-50"
                  >
                    Switch Identity
                  </button>

                  <button
                    type="button"
                    onClick={logout}
                    className="text-xs text-red-600 hover:text-red-800 font-medium px-2.5 py-1 rounded hover:bg-red-50"
                  >
                    Log Out
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setModalOpen(true)}
                  className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-3 py-1.5 rounded-md"
                >
                  Select Identity
                </button>
              )}
            </div>
          </div>
        </div>
      </nav>

      <DevAuthModal
        isOpen={modalOpen || !isAuthenticated}
        onClose={() => setModalOpen(false)}
        canDismiss={isAuthenticated}
      />
    </>
  );
}

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navigation />
      <main className="flex-1">{children}</main>
    </div>
  );
}

function AppRoutes() {
  const { isAuthenticated, isMerchant, merchantId } = useAuth();

  if (!isAuthenticated) {
    return (
      <div className="max-w-7xl mx-auto p-12 text-center">
        <p className="text-gray-500 text-sm">Please select a development identity to begin.</p>
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          isMerchant && merchantId ? (
            <Navigate to={`/merchants/${merchantId}`} replace />
          ) : (
            <Dashboard />
          )
        }
      />
      <Route
        path="/merchants"
        element={
          isMerchant && merchantId ? (
            <Navigate to={`/merchants/${merchantId}`} replace />
          ) : (
            <Merchants />
          )
        }
      />
      <Route path="/merchants/:merchantId" element={<Merchants />} />
      <Route
        path="/merchants/:merchantId/shoppers/:shopperId"
        element={<ShopperIntelligence />}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <Layout>
        <AppRoutes />
      </Layout>
    </AuthProvider>
  );
}

export default App;
