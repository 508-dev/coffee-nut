import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch, setAccessToken } from "./client";

vi.mock("$env/static/public", () => ({ PUBLIC_API_BASE_URL: "http://api.test/api/v1" }));

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

/** Headers of the nth fetch call, failing loudly if it never happened. */
function headersOf(mock: ReturnType<typeof vi.fn>, index = 0): Headers {
  const init = mock.mock.calls[index]?.[1] as RequestInit | undefined;
  if (!init) throw new Error(`fetch was not called ${index + 1} time(s)`);
  return init.headers as Headers;
}

describe("apiFetch", () => {
  beforeEach(() => {
    setAccessToken(null);
    vi.restoreAllMocks();
  });

  it("attaches the bearer token when one is set", async () => {
    setAccessToken("token-abc");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/brews/");

    expect(headersOf(fetchMock).get("authorization")).toBe("Bearer token-abc");
  });

  it("sends no bearer token for anonymous requests", async () => {
    setAccessToken("token-abc");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, {}));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/public/brews/xyz/", { anonymous: true });

    expect(headersOf(fetchMock).get("authorization")).toBeNull();
  });

  it("refreshes once on 401 and replays the request", async () => {
    setAccessToken("stale");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { type: "not_authenticated" }))
      .mockResolvedValueOnce(jsonResponse(200, { access: "fresh" }))
      .mockResolvedValueOnce(jsonResponse(200, { id: "brew-1" }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiFetch<{ id: string }>("/brews/");

    expect(result).toEqual({ id: "brew-1" });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(headersOf(fetchMock, 2).get("authorization")).toBe("Bearer fresh");
  });

  it("refreshes only once for concurrent 401s", async () => {
    setAccessToken("stale");
    let refreshCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith("/auth/token/refresh/")) {
          refreshCalls += 1;
          return jsonResponse(200, { access: "fresh" });
        }
        return refreshCalls === 0 ? jsonResponse(401, {}) : jsonResponse(200, { ok: true });
      }),
    );

    await Promise.all([apiFetch("/brews/"), apiFetch("/bags/"), apiFetch("/coffees/")]);

    expect(refreshCalls).toBe(1);
  });

  it("does not retry anonymous requests on 401", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(401, { type: "not_authenticated", detail: "", errors: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiFetch("/public/brews/xyz/", { anonymous: true })).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("gives up after one failed refresh instead of looping", async () => {
    setAccessToken("stale");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, {}))
      .mockResolvedValueOnce(jsonResponse(401, { detail: "refresh expired" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiFetch("/brews/")).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("exposes field errors keyed for form display", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(400, {
          type: "validation_error",
          detail: "Invalid input.",
          errors: [{ field: "dose_grams", code: "min_value", message: "Must be greater than 0." }],
        }),
      ),
    );

    let caught: unknown;
    try {
      await apiFetch("/brews/", { method: "POST", body: {} });
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).status).toBe(400);
    expect((caught as ApiError).fieldErrors()).toEqual({
      dose_grams: "Must be greater than 0.",
    });
  });

  it("returns undefined for 204 rather than parsing an empty body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    await expect(apiFetch("/brews/abc/", { method: "DELETE" })).resolves.toBeUndefined();
  });
});
