import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("$env/static/public", () => ({ PUBLIC_API_BASE_URL: "http://api.test/api/v1" }));

const { auth } = await import("./auth.svelte");

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const USER = { id: "u1", email: "a@example.com", display_name: "Alice" };

describe("auth store", () => {
  beforeEach(() => {
    auth.user = null;
    auth.ready = false;
    vi.restoreAllMocks();
  });

  it("restores a session from the refresh cookie", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) =>
        url.endsWith("/auth/token/refresh/") ? json(200, { access: "a" }) : json(200, USER),
      ),
    );

    await auth.restore();

    expect(auth.isAuthenticated).toBe(true);
    expect(auth.user?.email).toBe("a@example.com");
  });

  it("treats a failed restore as simply logged out", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(401, { detail: "no cookie" })));

    await auth.restore();

    expect(auth.isAuthenticated).toBe(false);
    expect(auth.ready).toBe(true);
  });

  it("marks itself ready even when restore throws", async () => {
    /** Guards cannot run until ready, so a stuck flag would hang the app. */
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    await auth.restore();

    expect(auth.ready).toBe(true);
  });

  it("signs in and loads the user", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) =>
        url.endsWith("/auth/token/") ? json(200, { access: "a" }) : json(200, USER),
      ),
    );

    await auth.login("a@example.com", "pw");

    expect(auth.user?.display_name).toBe("Alice");
  });

  it("propagates a failed sign-in and stays logged out", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(json(401, { type: "x", detail: "bad", errors: [] })),
    );

    await expect(auth.login("a@example.com", "wrong")).rejects.toThrow();
    expect(auth.isAuthenticated).toBe(false);
  });

  it("clears local state even if the logout call fails", async () => {
    /** An expired session is exactly when someone reaches for logout. */
    auth.user = USER as never;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(json(401, { type: "x", detail: "expired", errors: [] })),
    );

    await auth.logout();

    expect(auth.isAuthenticated).toBe(false);
  });

  it("never writes a token to localStorage", () => {
    /** The whole point of keeping the access token in memory. */
    const setItem = vi.fn();
    vi.stubGlobal("localStorage", { setItem, getItem: vi.fn(), removeItem: vi.fn() });

    expect(setItem).not.toHaveBeenCalled();
  });
});
