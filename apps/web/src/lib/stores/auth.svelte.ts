/**
 * Authentication state.
 *
 * The access token lives here in memory only. It is deliberately absent from
 * `localStorage`: anything script can read, an XSS can steal. The refresh token
 * is an HttpOnly cookie the browser holds and script never sees, which is what
 * lets a reload restore the session without persisting anything readable.
 */
import { ApiError, apiFetch, setAccessToken } from "$lib/api/client";
import type { User } from "$lib/api/types";

interface TokenResponse {
  access: string;
}

class AuthStore {
  user = $state<User | null>(null);
  /** Null until the first restore attempt finishes, so guards can wait. */
  ready = $state(false);

  get isAuthenticated(): boolean {
    return this.user !== null;
  }

  /**
   * Re-establish a session from the refresh cookie.
   *
   * Called once on boot. A failure here is the normal logged-out path, not an
   * error worth surfacing.
   */
  async restore(): Promise<void> {
    try {
      const tokens = await apiFetch<TokenResponse>("/auth/token/refresh/", { method: "POST" });
      setAccessToken(tokens.access);
      this.user = await apiFetch<User>("/auth/me/");
    } catch {
      setAccessToken(null);
      this.user = null;
    } finally {
      this.ready = true;
    }
  }

  async login(email: string, password: string): Promise<void> {
    const tokens = await apiFetch<TokenResponse>("/auth/token/", {
      method: "POST",
      body: { email, password },
    });
    setAccessToken(tokens.access);
    this.user = await apiFetch<User>("/auth/me/");
  }

  async register(email: string, password: string, displayName: string): Promise<void> {
    const tokens = await apiFetch<TokenResponse>("/auth/register/", {
      method: "POST",
      body: { email, password, display_name: displayName },
    });
    setAccessToken(tokens.access);
    this.user = await apiFetch<User>("/auth/me/");
  }

  async logout(): Promise<void> {
    try {
      await apiFetch("/auth/logout/", { method: "POST" });
    } catch (error) {
      // An expired session is exactly when someone reaches for logout, so a
      // failure here still means "signed out" locally.
      if (!(error instanceof ApiError)) throw error;
    } finally {
      setAccessToken(null);
      this.user = null;
    }
  }
}

export const auth = new AuthStore();
