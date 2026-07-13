export interface Identity {
  customer_id: string;
  email: string;
  role: string;
}

export interface OrderItem {
  product_id: string;
  product_name?: string | null;
  category?: string | null;
  quantity: number;
  unit_price?: number | null;
}

export interface Payment {
  payment_id?: string | null;
  payment_type?: string | null;
  payment_value?: number | null;
  installments?: number | null;
}

export interface Order {
  order_id: string;
  status: string;
  purchase_date?: string | null;
  delivered_date?: string | null;
  estimated_delivery_date?: string | null;
  payment_type?: string | null;
  payment_value?: number | null;
  installments?: number | null;
  payments?: Payment[];
  delivery_late?: boolean;
  items?: OrderItem[];
}

export interface Ticket {
  ticket_id: string;
  category: string;
  subject: string;
  status: string;
  created_at: string;
  order_id?: string | null;
}

export interface ServiceRequest {
  request_id: string;
  type: string;
  reason: string;
  status: string;
  evidence?: string | null;
  created_at: string;
  resolved_at?: string | null;
  order_id?: string | null;
}

export interface Citation {
  source?: string;
  title?: string;
  chunk_id?: string;
}

export interface ActionCard {
  action: string;
  request_id?: string | null;
  ticket_id?: string | null;
  order_id?: string | null;
  amount?: number | null;
  status?: string | null;
  next_step?: string | null;
  reason?: string | null;
  success?: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  action_taken?: string | null;
  action_card?: ActionCard | null;
  confirmation_prompt?: string | null;
  intent?: string;
}
