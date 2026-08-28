<script lang="ts">
import { goto } from "$app/navigation";
import { page } from "$app/state";
import { apiFetch } from "$lib/api/client";
import { toFormErrors } from "$lib/api/errors";
import { bags, brews, grinders as grindersApi, referenceSearch } from "$lib/api/resources";
import type { Bag, BrewMethod, Expanded, Grinder, Paginated } from "$lib/api/types";
import { toApiNumber as num, toApiText } from "$lib/api/values";
import BrewFields, { type BrewValues } from "$lib/components/BrewFields.svelte";
import Field from "$lib/components/Field.svelte";
import ReferencePicker from "$lib/components/ReferencePicker.svelte";

const bagId = page.params.id as string;

let methodId = $state("");
let methods = $state<BrewMethod[]>([]);

// Methods are also held in state so the schema below can react to the
// selection; assigning inside the loader keeps that out of the template.
const setup = (async () => {
  const [bag, methodPage, grinderPage] = await Promise.all([
    bags.get<Expanded<Bag, "coffee">>(bagId, { expand: "coffee" }),
    apiFetch<Paginated<BrewMethod>>("/brew-methods/?page_size=50"),
    grindersApi.list<Grinder>({ page_size: 50 }),
  ]);
  methods = methodPage.results;
  return { bag, methods: methodPage.results, grinders: grinderPage.results };
})();
// Prefilled with now, and editable — the brief asks for exactly that.
let brewedAt = $state(
  new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16),
);
let liked = $state<"" | "yes" | "no">("");
let notes = $state("");
let tastingNotes = $state<string[]>([]);
let noteToAdd = $state<string | null>(null);
let noteLabels = $state<Record<string, string>>({});

const AXES = ["acidity", "sweetness", "body", "bitterness", "aftertaste"] as const;
let taste = $state<Record<string, string | number | null>>({
  acidity: "",
  sweetness: "",
  body: "",
  bitterness: "",
  aftertaste: "",
});

let values = $state<BrewValues>({
  dose_grams: "",
  water_grams: "",
  water_temp_c: "",
  grinder: "",
  grind_setting: "",
  grind_microns: "",
  total_time_seconds: "",
  bloom_time_seconds: "",
  bloom_water_grams: "",
  pressure_bar: "",
  yield_grams: "",
});

let errors = $state<Record<string, string>>({});
let message = $state("");
let busy = $state(false);

const schema = $derived(
  (methods.find((m) => m.id === methodId)?.parameter_schema ?? null) as {
    fields?: string[];
    required?: string[];
  } | null,
);

function addNote(id: string | null, row: { name: string } | null) {
  if (id && row && !tastingNotes.includes(id)) {
    tastingNotes = [...tastingNotes, id];
    noteLabels = { ...noteLabels, [id]: row.name };
  }
  noteToAdd = null;
}

async function submit(event: SubmitEvent) {
  event.preventDefault();
  busy = true;
  errors = {};
  message = "";
  try {
    const created = await brews.create({
      bag: bagId,
      method: methodId,
      brewed_at: new Date(brewedAt).toISOString(),
      dose_grams: num(values.dose_grams),
      water_grams: num(values.water_grams),
      water_temp_c: num(values.water_temp_c),
      grinder: values.grinder || null,
      grind_setting: toApiText(values.grind_setting),
      grind_microns: num(values.grind_microns),
      total_time_seconds: num(values.total_time_seconds),
      bloom_time_seconds: num(values.bloom_time_seconds),
      bloom_water_grams: num(values.bloom_water_grams),
      pressure_bar: num(values.pressure_bar),
      yield_grams: num(values.yield_grams),
      liked: liked === "" ? null : liked === "yes",
      tasting_notes: tastingNotes,
      notes,
      ...Object.fromEntries(AXES.map((a) => [a, num(taste[a] ?? "")])),
    });
    await goto(`/brews/${created.id}/`);
  } catch (error) {
    ({ fields: errors, message } = toFormErrors(error));
  } finally {
    busy = false;
  }
}
</script>

{#await setup}
  <p class="muted">Loading…</p>
{:then data}
  <h1>Record a brew</h1>
  <p class="muted">{data.bag.coffee?.name}</p>

  <form onsubmit={submit}>
    <Field label="Method" error={errors.method}>
      <select bind:value={methodId} required>
        <option value="" disabled>Choose a method…</option>
        {#each data.methods as method (method.id)}
          <option value={method.id}>{method.name}</option>
        {/each}
      </select>
    </Field>

    <Field label="Brewed at" error={errors.brewed_at}>
      <input type="datetime-local" bind:value={brewedAt} />
    </Field>

    {#if methodId}
      <BrewFields bind:values {schema} grinders={data.grinders} {errors} />
    {:else}
      <p class="muted">Pick a method to see the fields that apply to it.</p>
    {/if}

    <fieldset>
      <legend>How was it?</legend>

      <Field label="Verdict" error={errors.liked}>
        <select bind:value={liked}>
          <option value="">Not rated</option>
          <option value="yes">Thumbs up</option>
          <option value="no">Thumbs down</option>
        </select>
      </Field>

      {#if tastingNotes.length}
        <ul class="chips">
          {#each tastingNotes as id (id)}
            <li>
              {noteLabels[id] ?? "note"}
              <button
                type="button"
                aria-label="Remove"
                onclick={() => (tastingNotes = tastingNotes.filter((n) => n !== id))}>×</button
              >
            </li>
          {/each}
        </ul>
      {/if}

      <ReferencePicker
        kind="tastingNotes"
        label="Tasting notes"
        bind:value={noteToAdd}
        onselect={addNote}
        hint="Search or add your own descriptor."
      />

      <div class="axes">
        {#each AXES as axis (axis)}
          <Field label={axis} error={errors[axis]}>
            <input type="number" min="1" max="5" step="1" bind:value={taste[axis]} />
          </Field>
        {/each}
      </div>

      <Field label="Notes" error={errors.notes}>
        <textarea bind:value={notes} rows="3" placeholder="Flowery, light…"></textarea>
      </Field>
    </fieldset>

    {#if message}<p class="field-error">{message}</p>{/if}

    <button type="submit" disabled={busy || !methodId}>
      {busy ? "Saving…" : "Save brew"}
    </button>
  </form>
{:catch}
  <h1>Not found</h1>
  <p class="muted">That bag does not exist, or is not yours.</p>
{/await}

<style>
  fieldset {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: var(--gap);
    margin: var(--gap) 0;
  }

  legend {
    padding: 0 0.25rem;
    color: var(--text-muted);
    font-size: 0.875rem;
  }

  .axes {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr));
    gap: var(--gap-sm);
  }

  .axes :global(label > span:first-child) {
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
    padding: 0.125rem 0.25rem 0.125rem 0.5rem;
    font-size: 0.875rem;
  }

  .chips button {
    background: none;
    border: none;
    color: var(--text-muted);
    padding: 0 0.25rem;
    cursor: pointer;
  }
</style>
