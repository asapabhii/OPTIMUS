const API_BASE = import.meta.env.VITE_API_URL || "";

interface RequestOptions {
  params?: Record<string, string>;
  headers?: Record<string, string>;
  rawBody?: boolean;
}

interface ApiResponse<T> {
  data: T;
  status: number;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options?: RequestOptions
): Promise<ApiResponse<T>> {
  let url = `${API_BASE}${path}`;

  if (options?.params) {
    const searchParams = new URLSearchParams(options.params);
    url += `?${searchParams.toString()}`;
  }

  const headers: Record<string, string> = {};

  // For FormData, don't set Content-Type (browser sets multipart boundary)
  const isFormData = body instanceof FormData;
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }

  // Attach JWT token if available (skip for auth endpoints)
  const token = localStorage.getItem("token");
  if (token && !path.includes("/auth/login") && !path.includes("/auth/signup")) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Merge custom headers
  if (options?.headers) {
    Object.assign(headers, options.headers);
    // Don't override Content-Type for FormData
    if (isFormData) {
      delete headers["Content-Type"];
    }
  }

  const fetchBody = isFormData
    ? (body as FormData)
    : body
    ? JSON.stringify(body)
    : undefined;

  const response = await fetch(url, {
    method,
    headers,
    body: fetchBody,
  });

  // If 401, clear token and redirect to login
  if (response.status === 401 && !path.includes("/auth/login")) {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    window.location.href = "/login";
    throw new Error("Session expired");
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `API error: ${response.status} ${response.statusText}`
    );
  }

  const data = await response.json();
  return { data, status: response.status };
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>("GET", path, undefined, options),
  post: <T>(path: string, body: unknown, options?: RequestOptions) =>
    request<T>("POST", path, body, options),
  put: <T>(path: string, body: unknown, options?: RequestOptions) =>
    request<T>("PUT", path, body, options),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>("DELETE", path, undefined, options),
};

// Auth helpers
export function isAuthenticated(): boolean {
  return !!localStorage.getItem("token");
}

export function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("username");
  localStorage.removeItem("user_id");
  localStorage.removeItem("user_role");
  localStorage.removeItem("company_domain");
  localStorage.removeItem(SESSIONS_KEY);
  window.location.href = "/login";
}

const SESSIONS_KEY = "optimus_chat_sessions";

export function getUsername(): string {
  return localStorage.getItem("username") || "";
}

export function getUserId(): string {
  return localStorage.getItem("user_id") || "00000000-0000-0000-0000-000000000001";
}

export function getUserRole(): string {
  return localStorage.getItem("user_role") || "user";
}

export function getCompanyDomain(): string {
  return localStorage.getItem("company_domain") || "";
}
