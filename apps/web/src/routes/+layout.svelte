<script lang="ts">
import { onMount } from "svelte";
import { page } from "$app/state";
import { auth } from "$lib/stores/auth.svelte";
import "../app.css";

let { children } = $props();

// Public share pages need no session, so skip the restore there entirely.
// Beyond saving a request, it stops an anonymous visit from rotating a
// signed-in user's refresh token for a page that never uses it.
const isPublicRoute = page.url.pathname.startsWith("/s/");

// One restore attempt on boot, before any guard runs. Guards wait on
// auth.ready so a reload does not bounce a signed-in user to /login.
onMount(() => {
  if (isPublicRoute) {
    auth.ready = true;
    return;
  }
  void auth.restore();
});
</script>

{#if auth.ready}
  {@render children()}
{:else}
  <main><p class="muted">Loading…</p></main>
{/if}
