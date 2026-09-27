export interface OrderResponse {
  order_id: string;
  merchant_id: string;
  shopper_id: string;
  order_status: string;
  currency: string;
  total_amount: number;
  placed_at: string;
  completed_at: string | null;
  cancelled_at: string | null;
}
