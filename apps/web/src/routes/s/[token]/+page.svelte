<script lang="ts">
import { page } from "$app/state";
import { apiFetch } from "$lib/api/client";
import type { PublicBrew } from "$lib/api/types";

// Outside the (app) group on purpose: no auth guard, and `anonymous: true`
// so a stale token never turns a public page into a sign-in prompt.
const load = apiFetch<PublicBrew>(`/public/brews/${page.params.token}/`, {
  anonymous: true,
});

function celsius(value: string | null | undefined): string {
  return value ? `${Number(value)} °C` : "—";
}

function grams(value: string | null | undefined): string {
  return value ? `${Number(value)} g` : "—";
}

function brewedOn(value: string | undefined): string {
  return value ? new Date(value).toLocaleDateString() : "an unrecorded date";
}

function seconds(value: number | null | undefined): string {
  if (value == null) return "—";
  const m = Math.floor(value / 60);
  const s = value % 60;
  return m ? `${m}m ${s}s` : `${s}s`;
}
</script>

<main>
  {#await load}
    <p class="muted">Loading brew…</p>
  {:then brew}
    <article class="stack">
      <header>
        <h1>{brew.bag?.coffee?.name}</h1>
        <p class="muted">
          {brew.method} &middot; brewed {brewedOn(brew.brewed_at)}
          {#if brew.shared_by} &middot; shared by {brew.shared_by}{/if}
        </p>
        {#if brew.liked === true}
          <p class="verdict">Thumbs up</p>
        {:else if brew.liked === false}
          <p class="verdict muted">Thumbs down</p>
        {/if}
      </header>

      <section class="card">
        <h2>The bean</h2>
        <dl>
          {#if brew.bag?.coffee?.roaster}
            <dt>Roaster</dt><dd>{brew.bag.coffee.roaster}</dd>
          {/if}
          {#if brew.bag?.coffee?.country}
            <dt>Origin</dt>
            <dd>
              {brew.bag.coffee.country}{#if brew.bag.coffee.region}, {brew.bag.coffee.region}{/if}
            </dd>
          {/if}
          {#if brew.bag?.coffee?.process}
            <dt>Process</dt><dd>{brew.bag.coffee.process}</dd>
          {/if}
          {#if brew.bag?.roast_date}
            <dt>Roasted</dt><dd>{brew.bag.roast_date}</dd>
          {/if}
        </dl>
      </section>

      <section class="card">
        <h2>The recipe</h2>
        <dl>
          <dt>Coffee</dt><dd>{grams(brew.dose_grams)}</dd>
          <dt>Water</dt><dd>{grams(brew.water_grams)}</dd>
          {#if brew.ratio}<dt>Ratio</dt><dd>1:{Number(brew.ratio)}</dd>{/if}
          <dt>Temperature</dt><dd>{celsius(brew.water_temp_c)}</dd>
          {#if brew.grind_setting}
            <dt>Grind</dt>
            <dd>{brew.grind_setting}{#if brew.grinder} on a {brew.grinder}{/if}</dd>
          {/if}
          {#if brew.total_time_seconds}
            <dt>Time</dt><dd>{seconds(brew.total_time_seconds)}</dd>
          {/if}
          {#if brew.yield_grams}<dt>Yield</dt><dd>{grams(brew.yield_grams)}</dd>{/if}
        </dl>
      </section>

      {#if brew.tasting_notes?.length || brew.notes}
        <section class="card">
          <h2>How it tasted</h2>
          {#if brew.tasting_notes?.length}
            <ul class="notes">
              {#each brew.tasting_notes as note (note)}
                <li>{note}</li>
              {/each}
            </ul>
          {/if}
          {#if brew.notes}<p>{brew.notes}</p>{/if}
        </section>
      {/if}
    </article>
  {:catch}
    <h1>Brew not found</h1>
    <p class="muted">
      This link is not valid, or the person who shared it has since revoked it.
    </p>
  {/await}
</main>

<style>
  dl {
    display: grid;
    grid-template-columns: minmax(6rem, auto) 1fr;
    gap: var(--gap-sm) var(--gap);
    margin: 0;
  }

  dt {
    color: var(--text-muted);
    font-size: 0.875rem;
  }

  dd {
    margin: 0;
  }

  h2 {
    font-size: 1rem;
    margin-bottom: var(--gap-sm);
  }

  .verdict {
    font-weight: 600;
    margin: 0;
  }

  .notes {
    list-style: none;
    padding: 0;
    margin: 0 0 var(--gap);
    display: flex;
    flex-wrap: wrap;
    gap: var(--gap-sm);
  }

  .notes li {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.125rem 0.5rem;
    font-size: 0.875rem;
  }
</style>
