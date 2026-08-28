<script lang="ts">
import { brews } from "$lib/api/resources";
import type { Brew, Expanded } from "$lib/api/types";

type Row = Expanded<Brew, "method" | "bag">;

let onlyLiked = $state(false);
const load = $derived(
  brews.list<Row>({
    expand: "method,bag.coffee",
    liked: onlyLiked ? true : undefined,
  }),
);
</script>

<h1>Brews</h1>

<label class="inline">
  <input type="checkbox" bind:checked={onlyLiked} />
  <span>Only the good ones</span>
</label>

{#await load}
  <p class="muted">Loading…</p>
{:then page}
  {#if page.results.length === 0}
    <p class="muted">
      No brews yet. Start from a <a href="/bags/">bag</a>.
    </p>
  {:else}
    <ul class="brews">
      {#each page.results as brew (brew.id)}
        <li>
          <a href="/brews/{brew.id}/">
            <strong>{brew.method?.name ?? "Brew"}</strong>
            <span class="muted">
              {(brew.bag as { coffee?: { name?: string } } | null)?.coffee?.name ?? ""}
            </span>
          </a>
          <span class="muted">
            {brew.brewed_at ? new Date(brew.brewed_at).toLocaleDateString() : ""}
            {#if brew.liked === true}· up{:else if brew.liked === false}· down{/if}
          </span>
        </li>
      {/each}
    </ul>
  {/if}
{:catch}
  <p class="field-error">Could not load your brews.</p>
{/await}

<style>
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

  .brews {
    list-style: none;
    padding: 0;
  }

  .brews li {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
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
</style>
