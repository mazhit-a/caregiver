import { clearToken, getToken } from "./session";

export const REQUEST_TIMEOUT_MS = 10_000;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details: unknown = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = undefined;
  }
  const error = isRecord(body) ? body["error"] : undefined;
  if (isRecord(error) && typeof error["code"] === "string" && typeof error["message"] === "string") {
    return new ApiError(response.status, error["code"], error["message"], error["details"]);
  }
  return new ApiError(response.status, "http_error", "The request failed.");
}

interface SendOptions {
  method: "GET" | "POST" | "PUT" | "DELETE";
  path: string;
  body?: unknown;
  signal?: AbortSignal;
  /** Adds the X-Session-Token header when a token exists. */
  auth: boolean;
  /** Overrides the default timeout (role-play turns wait longer than the server's 12 s). */
  timeoutMs?: number;
}

/** One place for the timeout, the abort wiring and the error mapping. Never logs. */
async function send<T>({
  method,
  path,
  body,
  signal,
  auth,
  timeoutMs = REQUEST_TIMEOUT_MS,
}: SendOptions): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const onAbort = (): void => controller.abort();
  signal?.addEventListener("abort", onAbort);
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = auth ? getToken() : null;
  if (token) headers["X-Session-Token"] = token;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  try {
    const response = await fetch(`/api${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    if (!response.ok) throw await toApiError(response);
    // 204 and empty bodies (DELETE /phrases/:id) resolve to undefined.
    const text = response.status === 204 ? "" : await response.text();
    return (text === "" ? undefined : JSON.parse(text)) as T;
  } catch (err) {
    if (err instanceof ApiError) {
      if (auth && err.status === 401) clearToken();
      throw err;
    }
    if (timedOut) throw new ApiError(0, "timeout", "The request took too long.");
    if (signal?.aborted) throw err;
    throw new ApiError(0, "network_error", "Could not reach the server.");
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}

/** Public GET on same-origin /api. No session token, no body or response logging. */
export function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  return send<T>({ method: "GET", path, signal, auth: false });
}

export interface ApiRequestOptions {
  method: "GET" | "POST" | "PUT" | "DELETE";
  path: string;
  body?: unknown;
  signal?: AbortSignal;
  /** True: send X-Session-Token. A 401 clears the stored token. */
  auth: boolean;
  /** Default 10 s. */
  timeoutMs?: number;
}

/** Session-aware request (JSON body, same timeout and ApiError as apiGet). Never logs. */
export function apiRequest<T>(options: ApiRequestOptions): Promise<T> {
  return send<T>(options);
}
