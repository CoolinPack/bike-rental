export type Role = "client" | "owner" | "super_admin";

export interface Me {
  telegram_id: number;
  role: Role;
  is_super_admin: boolean;
  park_id: number | null;
  park_name: string | null;
  user: {
    id: number;
    first_name?: string;
    last_name?: string;
    username?: string;
    language_code?: string;
  };
}

export interface BikeItem {
  id: number;
  park_id: number;
  plate_number: string;
  model: string;
  engine_cc: number | null;
  daily_price: string;
  price_3_days?: string | null;
  price_7_days?: string | null;
  price_14_days?: string | null;
  price_30_days?: string | null;
  color: string | null;
  description: string | null;
  mileage_km: number;
  status: "available" | "rented" | "maintenance";
  rented_until?: string | null;
  photos: string[];
  videos: string[];
  created_at: string;
  license_required?: boolean;
}

export interface BookingItem {
  id: number;
  park_id: number;
  bike_id: number;
  plate_number: string;
  model: string;
  photos: string[];
  start_date: string;
  end_date: string;
  total_price: string;
  original_total_price?: string | null;
  extension_total_price?: string;
  status: "pending" | "active" | "completed" | "cancelled" | "rejected";
  created_at: string;
  client_name?: string | null;
  client_phone?: string | null;
  client_username?: string | null;
  deposit_comment?: string | null;
  client_telegram_id?: number;
}