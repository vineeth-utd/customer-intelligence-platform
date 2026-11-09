export type AccessScope = 'INTERNAL' | 'MERCHANT';

export interface Principal {
  user_id: string;
  scope: AccessScope;
  merchant_id?: string | null;
  email?: string | null;
  roles: string[];
}

export interface DevTokenRequest {
  user_id?: string;
  scope: AccessScope;
  merchant_id?: string;
  email?: string;
  roles?: string[];
}

export interface DevTokenResponse {
  access_token: string;
  token_type: string;
  principal: Principal;
}

export interface DevMerchantOption {
  merchant_id: string;
  merchant_name: string;
  shopify_store_id: string;
}

export interface DevPrincipalsResponse {
  internal: Principal;
  merchants: DevMerchantOption[];
}

