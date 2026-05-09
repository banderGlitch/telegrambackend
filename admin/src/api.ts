import type {
  AdminInsight,
  AdminLiveSessions,
  AdminMessageLogRow,
  AdminOutboundResult,
  AdminOverview,
  AdminUserDetail,
  AdminUsersPage,
} from "./types";

const TOKEN_KEY = "asteroid_admin_jwt";

export function getApiBase(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").trim();
  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(value: string | null): void {
  if (!value) sessionStorage.removeItem(TOKEN_KEY);
  else sessionStorage.setItem(TOKEN_KEY, value);
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function parseJson(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const url = `${getApiBase()}${path}`;
  let res: Response;
  try {
    res = await fetch(url, { ...init, headers });
  } catch (e) {
    const base = getApiBase();
    const hint =
      `Cannot reach API at ${base}. Start the backend (uvicorn), set admin/.env VITE_API_BASE_URL, ` +
      `restart \"npm run dev\", and ensure backend ALLOWED_ORIGINS includes ${window.location.origin}.`;
    throw new ApiError(
      e instanceof TypeError ? `${e.message}. ${hint}` : `${String(e)}. ${hint}`,
      0,
      null,
    );
  }
  if (res.status === 401) {
    setToken(null);
  }
  if (!res.ok) {
    const body = await parseJson(res);
    const msg =
      typeof body === "object" && body && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : res.statusText;
    throw new ApiError(msg, res.status, body);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function loginAdmin(password: string): Promise<{ accessToken: string; expiresInHours: number }> {
  return apiFetch("/api/admin/auth/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

export async function fetchOverview(): Promise<AdminOverview> {
  return apiFetch("/api/admin/overview");
}

export async function fetchUsers(params: {
  page: number;
  pageSize: number;
  search?: string;
  sort?: string;
}): Promise<AdminUsersPage> {
  const sp = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    sort: params.sort || "updated",
  });
  if (params.search?.trim()) sp.set("search", params.search.trim());
  return apiFetch(`/api/admin/users?${sp.toString()}`);
}

export async function fetchUserDetail(userId: number): Promise<AdminUserDetail> {
  return apiFetch(`/api/admin/users/${userId}`);
}

export async function sendDirectMessage(
  userId: number,
  text: string,
  parseMode?: string | null,
): Promise<AdminOutboundResult> {
  return apiFetch("/api/admin/messages/send", {
    method: "POST",
    body: JSON.stringify({ userId, text, parseMode: parseMode || null }),
  });
}

export async function broadcastMessage(
  text: string,
  parseMode?: string | null,
): Promise<AdminOutboundResult> {
  return apiFetch("/api/admin/messages/broadcast", {
    method: "POST",
    body: JSON.stringify({ text, parseMode: parseMode || null }),
  });
}

export async function fetchMessageLog(): Promise<{ items: AdminMessageLogRow[] }> {
  return apiFetch("/api/admin/messages/log?limit=50");
}

export async function fetchDormantInsight(days = 14, limit = 8): Promise<AdminInsight> {
  return apiFetch(`/api/admin/insights/dormant?days=${days}&limit=${limit}`);
}

export async function fetchLiveSessions(thresholdMinutes = 45): Promise<AdminLiveSessions> {
  return apiFetch(`/api/admin/sessions/live?threshold_minutes=${thresholdMinutes}&limit=80`);
}

export async function downloadUsersCsv(): Promise<void> {
  const token = getToken();
  if (!token) throw new ApiError("Not logged in", 401, null);
  const url = `${getApiBase()}/api/admin/export/users.csv`;
  let res: Response;
  try {
    res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    const hint = `Cannot reach API at ${getApiBase()}. Is uvicorn running?`;
    throw new ApiError(e instanceof TypeError ? `${e.message}. ${hint}` : String(e), 0, null);
  }
  if (!res.ok) {
    const body = await parseJson(res);
    throw new ApiError(res.statusText, res.status, body);
  }
  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = `asteroid_players_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(blobUrl);
}
