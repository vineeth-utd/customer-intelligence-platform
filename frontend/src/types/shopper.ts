export interface ShopperResponse {
  shopper_id: string;
  merchant_id: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  country: string | null;
  state: string | null;
  city: string | null;
  timezone: string | null;
  first_seen_at: string | null;
  last_seen_at: string | null;
}
