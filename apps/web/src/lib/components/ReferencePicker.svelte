<script lang="ts">
import { untrack } from "svelte";
import { toFormErrors } from "$lib/api/errors";
import {
  type ReferenceKind,
  type ReferenceRow,
  referenceCreate,
  referenceSearch,
} from "$lib/api/resources";

interface Props {
  kind: ReferenceKind;
  label: string;
  /** Selected id, or null. */
  value?: string | null;
  /** Name to prefill when editing an existing record. */
  display?: string;
  error?: string | undefined;
  hint?: string | undefined;
  /** Countries are ISO data; nothing user-created belongs there. */
  allowCreate?: boolean;
  /** Extra fields sent when creating, e.g. a region's country. */
  createWith?: Record<string, unknown>;
  /** Narrowing passed to the search, e.g. regions of one country. */
  searchWith?: Record<string, string | null | undefined>;
  onselect?: (id: string | null, row: ReferenceRow | null) => void;
}

let {
  kind,
  label,
  value = $bindable(null),
  display = "",
  error,
  hint,
  allowCreate = true,
  createWith = {},
  searchWith = {},
  onselect,
}: Props = $props();

// Initial value only: `display` prefills an edit form, and the user's
// typing owns the field from then on. untrack states that intent.
let query = $state(untrack(() => display));
let results = $state<ReferenceRow[]>([]);
let open = $state(false);
let busy = $state(false);
let createError = $state("");
let timer: ReturnType<typeof setTimeout> | undefined;

// The canonical/custom split is the whole point of the reference model, so it
// is surfaced rather than hidden: users should see when they are reusing our
// data versus their own.
function search(term: string) {
  clearTimeout(timer);
  // Debounced: one request per pause, not one per keystroke.
  timer = setTimeout(async () => {
    if (!term.trim()) {
      results = [];
      return;
    }
    try {
      const page = await referenceSearch(kind, term.trim(), searchWith);
      results = page.results;
    } catch {
      results = [];
    }
  }, 200);
}

function choose(row: ReferenceRow) {
  value = row.id;
  query = row.name;
  open = false;
  createError = "";
  onselect?.(row.id, row);
}

function clear() {
  value = null;
  query = "";
  results = [];
  onselect?.(null, null);
}

async function createEntry() {
  busy = true;
  createError = "";
  try {
    choose(await referenceCreate(kind, { name: query.trim(), ...createWith }));
  } catch (err) {
    createError = toFormErrors(err).fields.name ?? toFormErrors(err).message;
  } finally {
    busy = false;
  }
}

const exactMatch = $derived(
  results.some((r) => r.name.toLowerCase() === query.trim().toLowerCase()),
);
const canCreate = $derived(allowCreate && query.trim().length > 1 && !exactMatch);
</script>

<div class="picker">
  <label>
    <span>{label}</span>
    <input
      type="text"
      bind:value={query}
      oninput={(e) => {
        // Typing invalidates the previous choice: the field must never show one
        // name while holding another row's id.
        value = null;
        open = true;
        search(e.currentTarget.value);
      }}
      onfocus={() => (open = true)}
      onblur={() => setTimeout(() => (open = false), 150)}
      autocomplete="off"
      placeholder="Search or add…"
    />
    {#if hint}<span class="hint">{hint}</span>{/if}
  </label>

  {#if value}
    <button type="button" class="secondary clear" onclick={clear}>Clear</button>
  {/if}

  {#if open && (results.length > 0 || canCreate)}
    <ul class="results">
      {#each results as row (row.id)}
        <li>
          <button type="button" onclick={() => choose(row)}>
            {row.name}
            {#if !row.is_canonical}<em>yours</em>{/if}
          </button>
        </li>
      {/each}
      {#if canCreate}
        <li>
          <button type="button" onclick={createEntry} disabled={busy}>
            {busy ? "Adding…" : `Add "${query.trim()}"`}
          </button>
        </li>
      {/if}
    </ul>
  {/if}

  {#if createError}<p class="field-error">{createError}</p>{/if}
  {#if error}<p class="field-error">{error}</p>{/if}
</div>

<style>
  .picker {
    position: relative;
    margin-bottom: var(--gap);
  }

  .picker :global(label) {
    margin-bottom: 0;
  }

  .hint {
    font-size: 0.8125rem;
    color: var(--text-muted);
  }

  .clear {
    position: absolute;
    right: 0;
    top: 0;
    padding: 0 0.25rem;
    border: none;
    font-size: 0.8125rem;
  }

  .results {
    position: absolute;
    z-index: 10;
    left: 0;
    right: 0;
    margin: 0.25rem 0 0;
    padding: 0;
    list-style: none;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    max-height: 14rem;
    overflow-y: auto;
  }

  .results button {
    display: flex;
    justify-content: space-between;
    gap: var(--gap-sm);
    width: 100%;
    text-align: left;
    background: none;
    border: none;
    color: var(--text);
    padding: 0.4rem 0.625rem;
    border-radius: 0;
  }

  .results button:hover {
    background: var(--bg);
  }

  .results em {
    color: var(--text-muted);
    font-size: 0.8125rem;
    font-style: normal;
  }
</style>
