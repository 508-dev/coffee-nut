<script lang="ts">
import { goto } from "$app/navigation";
import { page } from "$app/state";
import { auth } from "$lib/stores/auth.svelte";

let { children } = $props();

// The guard for every authenticated route. The public share page sits outside
// this group precisely so it cannot inherit this by accident.
$effect(() => {
  if (!auth.isAuthenticated) {
    const next = encodeURIComponent(page.url.pathname);
    void goto(`/login/?next=${next}`, { replaceState: true });
  }
});
</script>

{#if auth.isAuthenticated}
  <header>
    <nav>
      <a href="/">coffee-nut</a>
      <a href="/coffees/">Coffees</a>
      <a href="/bags/">Bags</a>
      <a href="/brews/">Brews</a>
      <a href="/settings/">Settings</a>
    </nav>
  </header>
  <main>
    {@render children()}
  </main>
{/if}

<style>
  header {
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }

  nav {
    max-width: var(--measure);
    margin: 0 auto;
    padding: var(--gap-sm) var(--gap);
    display: flex;
    gap: var(--gap);
    flex-wrap: wrap;
  }

  nav a {
    text-decoration: none;
  }

  nav a:first-child {
    font-weight: 600;
    margin-right: auto;
  }
</style>
