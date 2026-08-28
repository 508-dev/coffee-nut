<script lang="ts">
import { bagStats, bags, brews } from "$lib/api/resources";
import type { Bag, Brew, Expanded } from "$lib/api/types";
import { auth } from "$lib/stores/auth.svelte";

type BrewRow = Expanded<Brew, "method" | "bag">;
type BagRow = Expanded<Bag, "coffee">;

const load = Promise.all([
  bagStats(),
  brews.list<BrewRow>({ expand: "method,bag.coffee", page_size: 5 }),
  bags.list<BagRow>({ expand: "coffee", is_finished: false, page_size: 5 }),
]);
</script>

<h1>Hello, {auth.user?.display_name || auth.user?.email}</h1>

{#await load}
  <p class="muted">Loading…</p>
{:then [stats, recentBrews, openBags]}
  <ul class="stats">
    <li class="card"><strong>{stats.brews}</strong><span class="muted">brews</span></li>
    <li class="card"><strong>{stats.open_bags}</strong><span class="muted">open bags</span></li>
    <li class="card"><strong>{stats.bags}</strong><span class="muted">bags total</span></li>
  </ul>

  <section>
    <div class="row">
      <h2>Open bags</h2>
      <a href="/bags/new/">Record a purchase</a>
    </div>
    {#if openBags.results.length === 0}
      <p class="muted">Nothing open. <a href="/coffees/new/">Add a coffee</a> to start.</p>
    {:else}
      <ul class="plain">
        {#each openBags.results as bag (bag.id)}
          <li>
            <a href="/bags/{bag.id}/">{bag.coffee?.name ?? "Bag"}</a>
            {#if bag.roast_date}<span class="muted"> · roasted {bag.roast_date}</span>{/if}
          </li>
        {/each}
      </ul>
    {/if}
  </section>

  <section>
    <div class="row">
      <h2>Recent brews</h2>
      <a href="/brews/">All brews</a>
    </div>
    {#if recentBrews.results.length === 0}
      <p class="muted">No brews yet.</p>
    {:else}
      <ul class="plain">
        {#each recentBrews.results as brew (brew.id)}
          <li>
            <a href="/brews/{brew.id}/">{brew.method?.name ?? "Brew"}</a>
            <span class="muted">
              {(brew.bag as { coffee?: { name?: string } } | null)?.coffee?.name ?? ""}
              {#if brew.liked === true}· liked{/if}
            </span>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
{:catch}
  <p class="field-error">Could not load your dashboard.</p>
{/await}

<style>
  .stats {
    list-style: none;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr));
    gap: var(--gap-sm);
    margin-bottom: var(--gap-lg);
  }

  .stats li {
    display: flex;
    flex-direction: column;
  }

  .stats strong {
    font-size: 1.5rem;
  }

  .row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--gap);
  }

  .plain {
    list-style: none;
    padding: 0;
  }

  .plain li {
    padding: 0.25rem 0;
  }
</style>
