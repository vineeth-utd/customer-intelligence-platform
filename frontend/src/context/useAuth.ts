import { createContext, useContext } from 'react';
import type { Principal, DevTokenRequest } from '../types';

export interface AuthContextType {
  token: string | null;
  principal: Principal | null;
  isAuthenticated: boolean;
  isInternal: boolean;
  isMerchant: boolean;
  merchantId: string | null;
  loginWithDevPrincipal: (req: DevTokenRequest) => Promise<void>;
  setManualToken: (token: string) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

