import adapter from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

/** @type {import('@sveltejs/kit').Config} */
export default {
  preprocess: vitePreprocess(),
  kit: {
    // Static SPA: one HTML fallback, client-side routing, no server runtime to
    // deploy. See docs/architecture.md §7.
    adapter: adapter({ fallback: "index.html", strict: false }),
    alias: { $lib: "src/lib" },
    // One .env at the repo root, shared with Django. svelte-kit sync reads this
    // config rather than vite.config.ts, so the directory must be declared here
    // for $env/static/public to be typed. Only PUBLIC_-prefixed names reach the
    // browser bundle, so Django secrets in the same file stay out of it.
    env: { dir: "../.." },
  },
};
