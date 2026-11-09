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
    try {
      localStorage.setItem("mizan_csrf", token);
    } catch {}
  } else {
    sessionStorage.removeItem("mizan_csrf");
    try {
      localStorage.removeItem("mizan_csrf");
    } catch {}
  }
}

export function getCsrfToken(): string | null {
  if (!currentCsrfToken) {
    currentCsrfToken =
      sessionStorage.getItem("mizan_csrf") ||
      (() => {
        try {
          return localStorage.getItem("mizan_csrf");
        } catch {
          return null;
        }
      })();
  }
  return currentCsrfToken;
}

export function setSessionToken(token: string | null): void {
  currentSessionToken = token;
  if (token) {
    sessionStorage.setItem("mizan_session_token", token);
    try {
      localStorage.setItem("mizan_session_token", token);
    } catch {}
  } else {
    sessionStorage.removeItem("mizan_session_token");
    try {
      localStorage.removeItem("mizan_session_token");
    } catch {}
  }
}

export function getSessionToken(): string | null {
  if (!currentSessionToken) {
    currentSessionToken =
      sessionStorage.getItem("mizan_session_token") ||
      (() => {
        try {
          return localStorage.getItem("mizan_session_token");
        } catch {
          return null;
        }
      })();
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

export function buildApiUrl(path: string): string {
  let base = getBaseUrl().replace(/\/+$/, "");
  if (!base.endsWith("/api/v1")) {
    base = `${base}/api/v1`;
  }
  let cleanPath = path.trim();
  if (cleanPath.startsWith("/api/v1")) {
    cleanPath = cleanPath.slice(7);
  } else if (cleanPath.startsWith("api/v1")) {
    cleanPath = cleanPath.slice(6);
  }
  if (!cleanPath.startsWith("/")) {
    cleanPath = `/${cleanPath}`;
  }
  if (cleanPath === "/") {
    return base;
  }
  return `${base}${cleanPath}`;
}

async function request<T>(path: string, init?: RequestInit, retryCount = 0): Promise<T> {
  const controller = new AbortController();
  // 65s timeout to handle free cloud cold wakeups gracefully
  const timeout = window.setTimeout(() => controller.abort(), 65000);

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
    const fullUrl = buildApiUrl(path);
    const response = await fetch(fullUrl, {
      ...init,
      headers,
      credentials: "include",
      signal: controller.signal,
    });

    const isJson = response.headers.get("content-type")?.includes("application/json");
    const body = isJson ? await response.json() : null;

    if (!response.ok) {
      // Auto-retry once on 502/503 for idempotent GET requests while server is waking up
      const isGet = !init?.method || init.method.toUpperCase() === "GET";
      if (isGet && (response.status === 502 || response.status === 503) && retryCount < 2) {
        await new Promise((res) => setTimeout(res, 2000 * (retryCount + 1)));
        return request<T>(path, init, retryCount + 1);
      }

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

    // Auto-retry once on network/abort errors for GET requests
    const isGet = !init?.method || init.method.toUpperCase() === "GET";
    if (isGet && retryCount < 1) {
      await new Promise((res) => setTimeout(res, 2500));
      return request<T>(path, init, retryCount + 1);
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        "Cloud backend server is waking up. Please allow a few moments and try again.",
        408,
        "TIMEOUT"
      );
    }
    throw new ApiError(
      "Could not connect to Mizan cloud backend. Please verify your connection or try again in a moment.",
      503,
      "NETWORK_ERROR"
    );
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
