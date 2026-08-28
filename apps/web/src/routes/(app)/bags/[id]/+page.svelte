<script lang="ts">
import { page } from "$app/state";
import { bags, brewsForBag } from "$lib/api/resources";
import type { Bag, Brew, Expanded } from "$lib/api/types";

type Detail = Expanded<Bag, "coffee" | "purchased_from">;
type BrewRow = Expanded<Brew, "method">;

const id = page.params.id as string;
const load = Promise.all([
  bags.get<Detail>(id, { expand: "coffee,purchased_from" }),
  brewsForBag<BrewRow>(id, { expand: "method" }),
]);

function verdict(liked: boolean | null | undefined): string {
  if (liked === true) return "Good";
  if (liked === false) return "Not great";
  return "Unrated";
}
</script>

{#await load}
  <p class="muted">Loading…</p>
{:then [bag, brewPage]}
  <h1>{bag.coffee?.name ?? "Bag"}</h1>
  <p class="muted">
    {[
      bag.purchase_date ? `bought ${bag.purchase_date}` : null,
      bag.roast_date ? `roasted ${bag.roast_date}` : null,
      bag.purchased_from?.name,
      bag.weight_grams ? `${Number(bag.weight_grams)} g` : null,
    ]
      .filter(Boolean)
      .join(" · ")}
  </p>

  {#if bag.notes}<p>{bag.notes}</p>{/if}

  <section>
    <div class="row">
      <h2>Brews</h2>
      <a href="/bags/{bag.id}/brews/new/">Record a brew</a>
    </div>

    {#if brewPage.results.length === 0}
      <p class="muted">No brews against this bag yet.</p>
    {:else}
      <!-- The brief's "show my friend the good one" flow: method and verdict
           are what you scan by, so they lead. -->
      <ul class="brews">
        {#each brewPage.results as brew (brew.id)}
          <li>
            <a href="/brews/{brew.id}/">
              <strong>{brew.method?.name ?? "Brew"}</strong>
              <span class="muted">
                {brew.brewed_at ? new Date(brew.brewed_at).toLocaleDateString() : ""}
              </span>
            </a>
            <span class="verdict" class:good={brew.liked === true} class:bad={brew.liked === false}>
              {verdict(brew.liked)}
            </span>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
{:catch}
  <h1>Not found</h1>
  <p class="muted">That bag does not exist, or is not yours.</p>
{/await}

<style>
  .row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--gap);
  }

  .brews {
    list-style: none;
    padding: 0;
  }

  .brews li {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--gap);
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--border);
  }

  .brews a {
    text-decoration: none;
    display: flex;
    gap: var(--gap-sm);
    align-items: baseline;
  }

  .verdict {
    font-size: 0.8125rem;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .verdict.good {
    color: var(--ok);
  }

  .verdict.bad {
    color: var(--danger);
  }
</style>
