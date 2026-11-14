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

/** Public GET on same-origin /api. No session token, no body or response logging. */
export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, REQUEST_TIMEOUT_MS);
  const onAbort = (): void => controller.abort();
  signal?.addEventListener("abort", onAbort);
  try {
    const response = await fetch(`/api${path}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    if (!response.ok) throw await toApiError(response);
    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (timedOut) throw new ApiError(0, "timeout", "The request took too long.");
    if (signal?.aborted) throw err;
    throw new ApiError(0, "network_error", "Could not reach the server.");
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}
