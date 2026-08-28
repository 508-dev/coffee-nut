<script lang="ts">
import { bags } from "$lib/api/resources";
import type { Bag, Expanded } from "$lib/api/types";

type Row = Expanded<Bag, "coffee" | "purchased_from">;

let showFinished = $state(false);
const load = $derived(
  bags.list<Row>({
    expand: "coffee,purchased_from",
    is_finished: showFinished ? undefined : false,
  }),
);
</script>

<header class="row">
  <h1>Bags</h1>
  <a href="/bags/new/">Record a purchase</a>
</header>

<label class="inline">
  <input type="checkbox" bind:checked={showFinished} />
  <span>Include finished bags</span>
</label>

{#await load}
  <p class="muted">Loading…</p>
{:then page}
  {#if page.results.length === 0}
    <p class="muted">No bags yet.</p>
  {:else}
    <ul class="cards">
      {#each page.results as bag (bag.id)}
        <li class="card">
          <a href="/bags/{bag.id}/"><strong>{bag.coffee?.name ?? "Bag"}</strong></a>
          <p class="muted">
            {[
              bag.purchase_date ? `bought ${bag.purchase_date}` : null,
              bag.roast_date ? `roasted ${bag.roast_date}` : null,
              bag.purchased_from?.name,
              bag.is_finished ? "finished" : null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </li>
      {/each}
    </ul>
  {/if}
{:catch}
  <p class="field-error">Could not load your bags.</p>
{/await}

<style>
  .row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--gap);
  }

  .inline {
    display: flex;
    align-items: center;
    gap: var(--gap-sm);
    margin-bottom: var(--gap);
  }

  .inline input {
    width: auto;
  }

  .inline span {
    margin: 0;
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
