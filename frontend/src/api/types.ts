export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role_title: string;
}

export interface Conversation {
  channel_id: string;
  channel_name: string | null;
  is_private: boolean;
  my_role: string;
  member_count: number;
  unread_count: number;
  is_direct: boolean;
  dm_peer_id: string | null;
  dm_peer_name: string | null;
}

export interface DirectoryUser {
  id: string;
  email: string;
  full_name: string;
  role_title: string;
}

export type MessageStatus = "active" | "edited" | "deleted";

export interface Message {
  id: string;
  channel_id: string;
  sender_id: string;
  content: string | null;
  status: MessageStatus;
}

// Estado optimista del cliente (D009) — nunca se persiste en la base de datos, solo existe
// mientras la request de envío está en vuelo.
export type DeliveryStatus = "pending" | "sent" | "failed";

export interface PendingMessage extends Message {
  delivery: DeliveryStatus;
  clientId: string;
}

export interface MessagePage {
  items: Message[];
  next_cursor: string | null;
}

export interface SearchResult {
  id: string;
  channel_id: string;
  sender_id: string;
  headline: string;
  rank: number;
}

export interface SearchPage {
  items: SearchResult[];
  next_cursor: string | null;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    correlation_id: string;
  };
}
