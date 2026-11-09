import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { setClientAuthToken, getClientAuthToken } from '../api/client';
import { authApi } from '../api/auth';
import type { Principal, AccessScope, DevTokenRequest } from '../types';
import { AuthContext } from './useAuth';


function decodeToken(token: string): Principal | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const jsonStr = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const payload = JSON.parse(jsonStr);

    if (payload.exp && payload.exp < Date.now() / 1000) {
      return null;
    }

    if (!payload.sub || !payload.scope) {
      return null;
    }

    return {
      user_id: payload.sub,
      scope: payload.scope as AccessScope,
      merchant_id: payload.merchant_id || null,
      email: payload.email || null,
      roles: Array.isArray(payload.roles) ? payload.roles : [],
    };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getClientAuthToken());
  const [principal, setPrincipal] = useState<Principal | null>(() => {
    const initialToken = getClientAuthToken();
    return initialToken ? decodeToken(initialToken) : null;
  });

  useEffect(() => {
    if (token) {
      const decoded = decodeToken(token);
      if (decoded) {
        setPrincipal(decoded);
        setClientAuthToken(token);
      } else {
        setTokenState(null);
        setPrincipal(null);
        setClientAuthToken(null);
      }
    } else {
      setPrincipal(null);
      setClientAuthToken(null);
    }
  }, [token]);

  const loginWithDevPrincipal = useCallback(async (req: DevTokenRequest) => {
    const res = await authApi.getDevToken(req);
    setTokenState(res.access_token);
    setPrincipal(res.principal);
    setClientAuthToken(res.access_token);
  }, []);

  const setManualToken = useCallback((manualToken: string) => {
    const decoded = decodeToken(manualToken);
    if (!decoded) {
      throw new Error('Invalid or expired JWT Bearer token');
    }
    setTokenState(manualToken);
    setPrincipal(decoded);
    setClientAuthToken(manualToken);
  }, []);

  const logout = useCallback(() => {
    setTokenState(null);
    setPrincipal(null);
    setClientAuthToken(null);
  }, []);

  const isAuthenticated = !!token && !!principal;
  const isInternal = principal?.scope === 'INTERNAL';
  const isMerchant = principal?.scope === 'MERCHANT';
  const merchantId = principal?.merchant_id || null;

  return (
    <AuthContext.Provider
      value={{
        token,
        principal,
        isAuthenticated,
        isInternal,
        isMerchant,
        merchantId,
        loginWithDevPrincipal,
        setManualToken,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
