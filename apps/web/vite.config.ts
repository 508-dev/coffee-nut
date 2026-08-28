import { sveltekit } from "@sveltejs/kit/vite";
// vitest/config, not vite: it is what widens defineConfig to accept `test`.
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [sveltekit()],
  // The environment contract lives in one .env at the repo root, shared with
  // Django. Only PUBLIC_-prefixed names reach the browser bundle, so Django
  // secrets in the same file are not exposed.
  envDir: "../..",
  server: {
    // Ports come from scripts/worktree-ports.sh so sibling worktrees coexist.
    host: process.env.WEB_HOST ?? "127.0.0.1",
    port: Number(process.env.WEB_PORT ?? 8730),
    strictPort: true,
  },
  test: {
    include: ["src/**/*.{test,spec}.{js,ts}"],
    environment: "node",
  },
});
