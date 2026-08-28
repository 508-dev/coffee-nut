/**
 * Thin fetch wrapper around the coffee-nut API.
 *
 * Deliberately hand-written rather than a generated runtime client: the bundle
 * budget in docs/architecture.md §7 is the reason. Response *types* are
 * generated from the OpenAPI schema; only this transport layer is by hand.
 *
 * Token handling, per docs/architecture.md §6:
 *   - the access token lives in memory only, never localStorage, so an XSS
 *     cannot read it;
 *   - the refresh token is an HttpOnly cookie the server sets, so script
 *     cannot read it either, which is why requests send credentials.
 */

import { PUBLIC_API_BASE_URL } from "$env/static/public";

export interface ApiFieldError {
  field: string | null;
  code: string;
  message: string;
}

export interface ApiErrorBody {
  type: string;
  detail: string;
  errors: ApiFieldError[];
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: ApiErrorBody,
  ) {
    super(body.detail);
    this.name = "ApiError";
  }

  /** Field errors keyed for direct display against form inputs. */
  fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const error of this.body.errors) {
      if (error.field) out[error.field] = error.message;
    }
    return out;
  }
}

let accessToken: string | null = null;
/** Single-flight lock: ten parallel 401s must trigger one refresh, not ten. */
let refreshInFlight: Promise<boolean> | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

async function refreshAccessToken(): Promise<boolean> {
  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${PUBLIC_API_BASE_URL}/auth/token/refresh/`, {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
      });
      if (!response.ok) {
        accessToken = null;
        return false;
      }
      const data = (await response.json()) as { access: string };
      accessToken = data.access;
      return true;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Skip auth entirely. Used by the public share page. */
  anonymous?: boolean;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, anonymous = false, headers, ...rest } = options;

  const send = async (): Promise<Response> => {
    const merged = new Headers(headers);
    if (body !== undefined) merged.set("content-type", "application/json");
    if (!anonymous && accessToken) merged.set("authorization", `Bearer ${accessToken}`);

    // Assigned conditionally rather than passed as undefined, because
    // exactOptionalPropertyTypes distinguishes "absent" from "undefined".
    const init: RequestInit = { ...rest, headers: merged, credentials: "include" };
    if (body !== undefined) init.body = JSON.stringify(body);

    return fetch(`${PUBLIC_API_BASE_URL}${path}`, init);
  };

  let response = await send();

  // One retry, and only for authenticated calls: an anonymous 401 means the
  // resource genuinely needs auth, not that our token went stale.
  if (response.status === 401 && !anonymous && (await refreshAccessToken())) {
    response = await send();
  }

  if (!response.ok) {
    throw new ApiError(response.status, (await response.json()) as ApiErrorBody);
  }

  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}
