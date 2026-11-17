import { useAuth } from "../store/auth";

const API_BASE = "/api";

async function request<T>(
  method: string,
  path: string,
  options: {
    body?: unknown;
    formData?: FormData;
    query?: Record<string, string | number | boolean | undefined>;
  } = {},
): Promise<T> {
  const { initData, mode } = useAuth.getState();

  let url = `${API_BASE}${path}`;
  if (options.query) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(options.query)) {
      if (v !== undefined && v !== null && v !== "") {
        params.set(k, String(v));
      }
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }

  const headers: Record<string, string> = {};
  if (initData) headers["X-Init-Data"] = initData;
  if (mode !== "auto") headers["X-Mode"] = mode;

  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const res = await fetch(url, { method, headers, body });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      message = data.detail || message;
    } catch {}
    throw new Error(message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, query?: Record<string, any>) =>
    request<T>("GET", path, { query }),
  post: <T>(path: string, body?: unknown, query?: Record<string, any>) =>
    request<T>("POST", path, { body, query }),
  patch: <T>(path: string, body?: unknown, query?: Record<string, any>) =>
    request<T>("PATCH", path, { body, query }),
  delete: <T>(path: string, query?: Record<string, any>) =>
    request<T>("DELETE", path, { query }),
  upload: <T>(path: string, formData: FormData, query?: Record<string, any>) =>
    request<T>("POST", path, { formData, query }),
};