<script lang="ts">
import { coffees } from "$lib/api/resources";
import type { Coffee, Expanded } from "$lib/api/types";

type Row = Expanded<Coffee, "roaster" | "country" | "process">;

const load = coffees.list<Row>({ expand: "roaster,country,process" });
</script>

<header class="row">
  <h1>Coffees</h1>
  <a href="/coffees/new/" class="button-link">Add coffee</a>
</header>

{#await load}
  <p class="muted">Loading…</p>
{:then page}
  {#if page.results.length === 0}
    <p class="muted">
      No coffees yet. A coffee is the product; each purchase of it is a bag.
    </p>
  {:else}
    <ul class="cards">
      {#each page.results as coffee (coffee.id)}
        <li class="card">
          <a href="/coffees/{coffee.id}/"><strong>{coffee.name}</strong></a>
          <p class="muted">
            {[coffee.roaster?.name, coffee.country?.name, coffee.process?.name]
              .filter(Boolean)
              .join(" · ") || "No origin details yet"}
          </p>
        </li>
      {/each}
    </ul>
  {/if}
{:catch}
  <p class="field-error">Could not load your coffees.</p>
{/await}

<style>
  .row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--gap);
  }

  .cards {
    list-style: none;
    padding: 0;
    display: grid;
    gap: var(--gap-sm);
  }

  .cards a {
    text-decoration: none;
  }

  .cards p {
    margin: 0.25rem 0 0;
    font-size: 0.875rem;
  }
</style>
