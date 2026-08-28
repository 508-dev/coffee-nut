<script lang="ts">
import { page } from "$app/state";
import { bags, coffees } from "$lib/api/resources";
import type { Bag, Coffee, Expanded } from "$lib/api/types";

type Detail = Expanded<Coffee, "roaster" | "country" | "region" | "producer" | "process">;

const id = page.params.id as string;
const load = Promise.all([
  coffees.get<Detail>(id, { expand: "roaster,country,region,producer,process" }),
  bags.list<Bag>({ coffee: id }),
]);
</script>

{#await load}
  <p class="muted">Loading…</p>
{:then [coffee, bagPage]}
  <h1>{coffee.name}</h1>

  <dl class="card">
    {#if coffee.roaster}<dt>Roaster</dt><dd>{coffee.roaster.name}</dd>{/if}
    {#if coffee.country}<dt>Country</dt><dd>{coffee.country.name}</dd>{/if}
    {#if coffee.region}<dt>Region</dt><dd>{coffee.region.name}</dd>{/if}
    {#if coffee.producer}<dt>Producer</dt><dd>{coffee.producer.name}</dd>{/if}
    {#if coffee.process}<dt>Process</dt><dd>{coffee.process.name}</dd>{/if}
    {#if coffee.harvest_year}<dt>Harvest</dt><dd>{coffee.harvest_year}</dd>{/if}
    {#if coffee.roast_level}<dt>Roast</dt><dd>{coffee.roast_level.replace("_", "-")}</dd>{/if}
    {#if coffee.is_decaf}<dt>Decaf</dt><dd>Yes</dd>{/if}
  </dl>

  {#if coffee.notes}<p>{coffee.notes}</p>{/if}

  <section>
    <div class="row">
      <h2>Bags</h2>
      <a href="/bags/new/?coffee={coffee.id}">Record a purchase</a>
    </div>
    {#if bagPage.results.length === 0}
      <p class="muted">No purchases recorded yet.</p>
    {:else}
      <ul class="plain">
        {#each bagPage.results as bag (bag.id)}
          <li>
            <a href="/bags/{bag.id}/">{bag.purchase_date ?? "Undated purchase"}</a>
            {#if bag.is_finished}<span class="muted"> · finished</span>{/if}
          </li>
        {/each}
      </ul>
    {/if}
  </section>
{:catch}
  <h1>Not found</h1>
  <p class="muted">That coffee does not exist, or is not yours.</p>
{/await}

<style>
  dl {
    display: grid;
    grid-template-columns: minmax(6rem, auto) 1fr;
    gap: var(--gap-sm) var(--gap);
    margin: 0 0 var(--gap);
  }

  dt {
    color: var(--text-muted);
    font-size: 0.875rem;
  }

  dd {
    margin: 0;
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
