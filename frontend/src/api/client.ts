import type {
  ApiErrorBody,
  Conversation,
  CurrentUser,
  Message,
  MessagePage,
  SearchPage,
  TokenPair,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const ACCESS_TOKEN_KEY = "sentinelly.access_token";
const REFRESH_TOKEN_KEY = "sentinelly.refresh_token";

export class ApiError extends Error {
  code: string;
  correlationId: string;
  status: number;

  constructor(status: number, code: string, message: string, correlationId: string) {
    super(message);
    this.status = status;
    this.code = code;
    this.correlationId = correlationId;
  }
}

export function getStoredTokens(): TokenPair | null {
  const access_token = localStorage.getItem(ACCESS_TOKEN_KEY);
  const refresh_token = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!access_token || !refresh_token) return null;
  return { access_token, refresh_token, token_type: "bearer" };
}

export function storeTokens(tokens: TokenPair): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function clearStoredTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// Notifica a AuthContext cuando el refresh también falla (sesión realmente terminada) sin
// crear una dependencia circular entre el cliente HTTP y el contexto de React.
type SessionExpiredListener = () => void;
let onSessionExpired: SessionExpiredListener | null = null;
export function setSessionExpiredListener(listener: SessionExpiredListener | null): void {
  onSessionExpired = listener;
}

async function parseError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody | null = null;
  try {
    body = await response.json();
  } catch {
    // respuesta sin cuerpo JSON (ej. timeout de red simulado en tests) — igual se reporta
  }
  const correlationId = response.headers.get("X-Correlation-ID") ?? "";
  if (body?.error) {
    return new ApiError(response.status, body.error.code, body.error.message, body.error.correlation_id || correlationId);
  }
  return new ApiError(response.status, "UNKNOWN_ERROR", response.statusText, correlationId);
}

async function refreshAccessToken(): Promise<boolean> {
  const tokens = getStoredTokens();
  if (!tokens) return false;
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: tokens.refresh_token }),
  });
  if (!response.ok) {
    clearStoredTokens();
    return false;
  }
  storeTokens(await response.json());
  return true;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | undefined>;
}

async function request<T>(path: string, options: RequestOptions = {}, isRetry = false): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`);
  for (const [key, value] of Object.entries(options.params ?? {})) {
    if (value !== undefined) url.searchParams.set(key, String(value));
  }

  const tokens = getStoredTokens();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (tokens) headers["Authorization"] = `Bearer ${tokens.access_token}`;

  const response = await fetch(url.toString(), {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 401 && tokens && !isRetry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return request<T>(path, options, true);
    onSessionExpired?.();
    throw await parseError(response);
  }

  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  login: (email: string, password: string) => request<TokenPair>("/auth/login", { method: "POST", body: { email, password } }),
  logout: (refresh_token: string) => request<void>("/auth/logout", { method: "POST", body: { refresh_token } }),
  getCurrentUser: () => request<CurrentUser>("/users/me"),
  listChannels: () => request<Conversation[]>("/channels"),
  getChannelMessages: (channelId: string, cursor?: string) =>
    request<MessagePage>(`/channels/${channelId}/messages`, { params: { cursor, limit: 30 } }),
  sendMessage: (channelId: string, content: string) =>
    request<Message>(`/channels/${channelId}/messages`, { method: "POST", body: { content } }),
  editMessage: (messageId: string, content: string) => request<Message>(`/messages/${messageId}`, { method: "PATCH", body: { content } }),
  deleteMessage: (messageId: string) => request<Message>(`/messages/${messageId}`, { method: "DELETE" }),
  searchMessages: (query: string, cursor?: string) =>
    request<SearchPage>("/messages/search", { params: { q: query, cursor, limit: 20 } }),
  // Fase 18 (bloqueada por falta de API key de un proveedor LLM al momento de escribir esto)
  // — el endpoint todavía no existe en el backend; CopilotPanel maneja el error con
  // gracia (t("copilot.unavailable")) hasta que se implemente.
  askCopilot: (question: string) =>
    request<{ answer: string; citations: { message_id: string; channel_id: string }[] }>("/copilot/ask", {
      method: "POST",
      body: { question },
    }),
};

export function wsUrlForChannel(channelId: string): string {
  const tokens = getStoredTokens();
  const base = (import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000") as string;
  return `${base}/ws/channels/${channelId}?token=${encodeURIComponent(tokens?.access_token ?? "")}`;
}
