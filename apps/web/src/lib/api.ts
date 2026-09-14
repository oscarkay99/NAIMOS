const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ACCESS_TOKEN_KEY = "naimos_access_token";
const REFRESH_TOKEN_KEY = "naimos_refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  const resp = await fetch(`${API_URL}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!resp.ok) return false;
  const data = await resp.json();
  setTokens(data.access_token, data.refresh_token);
  return true;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  isForm?: boolean;
  skipAuth?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}, retry = true): Promise<T> {
  const headers: Record<string, string> = {};
  if (!options.isForm) headers["Content-Type"] = "application/json";

  if (!options.skipAuth) {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const resp = await fetch(`${API_URL}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? (options.isForm ? (options.body as FormData) : JSON.stringify(options.body)) : undefined,
  });

  if (resp.status === 401 && retry && !options.skipAuth) {
    const refreshed = await tryRefresh();
    if (refreshed) return request<T>(path, options, false);
    clearTokens();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new ApiError(401, "Not authenticated");
  }

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail || detail;
    } catch {
      // ignore
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) return undefined as T;
  const contentType = resp.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return resp.json();
  return undefined as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  postForm: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form, isForm: true }),
  postSkipAuth: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body, skipAuth: true }),
};

export { API_URL };
