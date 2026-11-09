declare global {
  interface Window {
    __MIZAN_CONFIG__?: {
      API_BASE_URL?: string;
    };
  }
}

export function getBaseUrl(): string {
  if (typeof window !== "undefined" && window.__MIZAN_CONFIG__?.API_BASE_URL) {
    return window.__MIZAN_CONFIG__.API_BASE_URL.replace(/\/+$/, "");
  }
  return (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace(/\/+$/, "");
}

let currentCsrfToken: string | null = null;
let currentSessionToken: string | null = null;

export function setCsrfToken(token: string | null): void {
  currentCsrfToken = token;
  if (token) {
    sessionStorage.setItem("mizan_csrf", token);
  } else {
    sessionStorage.removeItem("mizan_csrf");
  }
}

export function getCsrfToken(): string | null {
  if (!currentCsrfToken) {
    currentCsrfToken = sessionStorage.getItem("mizan_csrf");
  }
  return currentCsrfToken;
}

export function setSessionToken(token: string | null): void {
  currentSessionToken = token;
  if (token) {
    sessionStorage.setItem("mizan_session_token", token);
  } else {
    sessionStorage.removeItem("mizan_session_token");
  }
}

export function getSessionToken(): string | null {
  if (!currentSessionToken) {
    currentSessionToken = sessionStorage.getItem("mizan_session_token");
  }
  return currentSessionToken;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly code?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 10000);

  const headers = new Headers(init?.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  if (!headers.has("Content-Type") && init?.body && typeof init.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  const csrf = getCsrfToken();
  if (csrf && ["POST", "PUT", "PATCH", "DELETE"].includes((init?.method ?? "GET").toUpperCase())) {
    headers.set("X-CSRF-Token", csrf);
  }

  const sessionToken = getSessionToken();
  if (sessionToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${sessionToken}`);
  }

  try {
    const response = await fetch(`${getBaseUrl()}${path}`, {
      ...init,
      headers,
      credentials: "include",
      signal: controller.signal,
    });

    const isJson = response.headers.get("content-type")?.includes("application/json");
    const body = isJson ? await response.json() : null;

    if (!response.ok) {
      const errorMessage =
        body?.error?.message ??
        body?.detail ??
        (typeof body === "string" ? body : `Request failed with status ${response.status}`);
      const errorCode = body?.error?.code ?? "API_ERROR";
      throw new ApiError(errorMessage, response.status, errorCode);
    }

    // Unpack data envelope if present
    return (body?.data !== undefined ? body.data : body) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timed out. Please check your connection.", 408, "TIMEOUT");
    }
    throw new ApiError("Could not connect to Mizan backend service.", 503, "NETWORK_ERROR");
  } finally {
    window.clearTimeout(timeout);
  }
}

export function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  return request<T>(path, { ...init, method: "GET" });
}

export function apiPost<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
  return request<T>(path, {
    ...init,
    method: "POST",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function apiPatch<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
  return request<T>(path, {
    ...init,
    method: "PATCH",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function apiPut<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
  return request<T>(path, {
    ...init,
    method: "PUT",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function apiDelete<T>(path: string, init?: RequestInit): Promise<T> {
  return request<T>(path, { ...init, method: "DELETE" });
}

export function apiUpload<T>(path: string, formData: FormData, init?: RequestInit): Promise<T> {
  return request<T>(path, {
    ...init,
    method: "POST",
    body: formData,
  });
}
