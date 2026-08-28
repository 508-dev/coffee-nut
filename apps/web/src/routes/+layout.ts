// SPA mode: render entirely on the client, emit one HTML fallback.
// docs/architecture.md §7 explains why we skip SSR here.
export const ssr = false;
export const prerender = false;
export const trailingSlash = "always";
