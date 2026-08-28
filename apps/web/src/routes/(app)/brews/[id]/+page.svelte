<script lang="ts">
import { page } from "$app/state";
import { toFormErrors } from "$lib/api/errors";
import { brews, shareBrew, unshareBrew } from "$lib/api/resources";
import type { Brew, Expanded } from "$lib/api/types";

type Detail = Expanded<Brew, "method" | "grinder" | "bag" | "tasting_notes">;

const id = page.params.id as string;

let brew = $state<Detail | null>(null);
let shareUrl = $state<string | null>(null);
let shared = $state(false);
let copied = $state(false);
let busy = $state(false);
let message = $state("");

const load = (async () => {
  const loaded = await brews.get<Detail>(id, {
    expand: "method,grinder,bag.coffee,tasting_notes",
  });
  brew = loaded;
  shared = Boolean(loaded.share_token);
  if (loaded.share_token) {
    // The API returns the token; the SPA owns the URL shape for /s/.
    shareUrl = `${window.location.origin}/s/${loaded.share_token}`;
  }
  return loaded;
})();

async function toggleShare(event: Event) {
  const wanted = (event.currentTarget as HTMLInputElement).checked;
  busy = true;
  message = "";
  copied = false;
  try {
    if (wanted) {
      const result = await shareBrew(id);
      shareUrl = `${window.location.origin}/s/${result.share_token}`;
      shared = true;
    } else {
      await unshareBrew(id);
      shareUrl = null;
      shared = false;
    }
  } catch (error) {
    message = toFormErrors(error).message;
    shared = !wanted;
  } finally {
    busy = false;
  }
}

async function copy() {
  if (!shareUrl) return;
  await navigator.clipboard.writeText(shareUrl);
  copied = true;
}

const AXES = ["acidity", "sweetness", "body", "bitterness", "aftertaste"] as const;
</script>

{#await load}
  <p class="muted">Loading…</p>
{:then loaded}
  <h1>{loaded.method?.name ?? "Brew"}</h1>
  <p class="muted">
    {(loaded.bag as { coffee?: { name?: string } } | null)?.coffee?.name ?? ""}
    {#if loaded.brewed_at}· {new Date(loaded.brewed_at).toLocaleString()}{/if}
  </p>

  <dl class="card">
    {#if loaded.dose_grams}<dt>Coffee</dt><dd>{Number(loaded.dose_grams)} g</dd>{/if}
    {#if loaded.water_grams}<dt>Water</dt><dd>{Number(loaded.water_grams)} g</dd>{/if}
    {#if loaded.ratio}<dt>Ratio</dt><dd>1:{Number(loaded.ratio)}</dd>{/if}
    {#if loaded.water_temp_c}<dt>Temperature</dt><dd>{Number(loaded.water_temp_c)} °C</dd>{/if}
    {#if loaded.grind_setting}
      <dt>Grind</dt>
      <dd>{loaded.grind_setting}{#if loaded.grinder} on {loaded.grinder.name}{/if}</dd>
    {/if}
    {#if loaded.total_time_seconds}<dt>Time</dt><dd>{loaded.total_time_seconds}s</dd>{/if}
    {#if loaded.yield_grams}<dt>Yield</dt><dd>{Number(loaded.yield_grams)} g</dd>{/if}
    <dt>Verdict</dt>
    <dd>
      {loaded.liked === true ? "Thumbs up" : loaded.liked === false ? "Thumbs down" : "Not rated"}
    </dd>
  </dl>

  {#if AXES.some((a) => loaded[a] != null)}
    <div class="card axes">
      {#each AXES as axis (axis)}
        {#if loaded[axis] != null}
          <div><span class="muted">{axis}</span><strong>{loaded[axis]}/5</strong></div>
        {/if}
      {/each}
    </div>
  {/if}

  {#if Array.isArray(loaded.tasting_notes) && loaded.tasting_notes.length}
    <ul class="chips">
      {#each loaded.tasting_notes as note (typeof note === "string" ? note : note.id)}
        <li>{typeof note === "string" ? note : note.name}</li>
      {/each}
    </ul>
  {/if}

  {#if loaded.notes}<p>{loaded.notes}</p>{/if}

  <section class="card">
    <h2>Share</h2>
    <label class="inline">
      <input type="checkbox" checked={shared} onchange={toggleShare} disabled={busy} />
      <span>Publicly shareable</span>
    </label>
    <p class="muted">
      Anyone with the link can read this brew and its bag details. No account needed.
    </p>

    {#if shared && shareUrl}
      <div class="share-row">
        <input readonly value={shareUrl} />
        <button type="button" onclick={copy}>{copied ? "Copied" : "Copy"}</button>
      </div>
    {/if}

    {#if message}<p class="field-error">{message}</p>{/if}
  </section>
{:catch}
  <h1>Not found</h1>
  <p class="muted">That brew does not exist, or is not yours.</p>
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

  .axes {
    display: flex;
    flex-wrap: wrap;
    gap: var(--gap);
    margin-bottom: var(--gap);
  }

  .axes div {
    display: flex;
    flex-direction: column;
    font-size: 0.875rem;
    text-transform: capitalize;
  }

  .chips {
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: var(--gap-sm);
    padding: 0;
    margin: 0 0 var(--gap);
  }

  .chips li {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.125rem 0.5rem;
    font-size: 0.875rem;
  }

  .inline {
    display: flex;
    align-items: center;
    gap: var(--gap-sm);
    margin-bottom: var(--gap-sm);
  }

  .inline input {
    width: auto;
  }

  .inline span {
    margin: 0;
  }

  .share-row {
    display: flex;
    gap: var(--gap-sm);
    margin-top: var(--gap-sm);
  }

  h2 {
    font-size: 1rem;
  }
</style>
