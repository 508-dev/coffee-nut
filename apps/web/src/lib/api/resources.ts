/**
 * Typed wrappers over the REST resources.
 *
 * Screens call these rather than building paths, so a route change is one edit
 * here instead of a search across components.
 */
import { apiFetch } from "./client";
import type { Bag, Brew, Coffee, Grinder, Paginated, User } from "./types";

type Query = Record<string, string | number | boolean | null | undefined>;

function qs(params: Query = {}): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

function crud<T>(base: string) {
  return {
    // `list<R>` and `get<R>` take an override type so a caller using ?expand=
    // can state the shape it actually receives. See `Expanded` in types.ts.
    list: <R = T>(params?: Query) => apiFetch<Paginated<R>>(`/${base}/${qs(params)}`),
    get: <R = T>(id: string, params?: Query) => apiFetch<R>(`/${base}/${id}/${qs(params)}`),
    create: (body: unknown) => apiFetch<T>(`/${base}/`, { method: "POST", body }),
    update: (id: string, body: unknown) =>
      apiFetch<T>(`/${base}/${id}/`, { method: "PATCH", body }),
    remove: (id: string) => apiFetch<void>(`/${base}/${id}/`, { method: "DELETE" }),
  };
}

export const coffees = crud<Coffee>("coffees");
export const bags = crud<Bag>("bags");
export const brews = crud<Brew>("brews");
export const grinders = crud<Grinder>("grinders");

/** Reference lookups. Every one of these accepts `?q=` for typeahead. */
export const REFERENCE_PATHS = {
  countries: "countries",
  regions: "regions",
  producers: "producers",
  roasters: "roasters",
  varietals: "varietals",
  processes: "processes",
  brewMethods: "brew-methods",
  tastingNotes: "tasting-notes",
} as const;

export type ReferenceKind = keyof typeof REFERENCE_PATHS;

export interface ReferenceRow {
  id: string;
  name: string;
  is_canonical: boolean;
  [key: string]: unknown;
}

export function referenceSearch(kind: ReferenceKind, term: string, params?: Query) {
  return apiFetch<Paginated<ReferenceRow>>(
    `/${REFERENCE_PATHS[kind]}/${qs({ q: term, page_size: 8, ...params })}`,
  );
}

export function referenceCreate(kind: ReferenceKind, body: Record<string, unknown>) {
  return apiFetch<ReferenceRow>(`/${REFERENCE_PATHS[kind]}/`, { method: "POST", body });
}

export const brewsForBag = <R = Brew>(bagId: string, params?: Query) =>
  apiFetch<Paginated<R>>(`/bags/${bagId}/brews/${qs(params)}`);

export const bagStats = () =>
  apiFetch<{ bags: number; open_bags: number; brews: number }>("/bags/stats/");

export const shareBrew = (id: string, rotate = false) =>
  apiFetch<{ share_token: string; share_url: string }>(`/brews/${id}/share/`, {
    method: "POST",
    body: { rotate },
  });

export const unshareBrew = (id: string) =>
  apiFetch<void>(`/brews/${id}/share/`, { method: "DELETE" });

export const updateMe = (body: unknown) => apiFetch<User>("/auth/me/", { method: "PATCH", body });
