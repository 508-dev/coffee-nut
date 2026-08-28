<script lang="ts">
import { goto } from "$app/navigation";
import { toFormErrors } from "$lib/api/errors";
import { coffees } from "$lib/api/resources";
import Field from "$lib/components/Field.svelte";
import ReferencePicker from "$lib/components/ReferencePicker.svelte";

let name = $state("");
let roaster = $state<string | null>(null);
let country = $state<string | null>(null);
let region = $state<string | null>(null);
let producer = $state<string | null>(null);
let process = $state<string | null>(null);
let harvestYear = $state("");
let roastLevel = $state("");
let isDecaf = $state(false);
let notes = $state("");

let errors = $state<Record<string, string>>({});
let message = $state("");
let busy = $state(false);

async function submit(event: SubmitEvent) {
  event.preventDefault();
  busy = true;
  errors = {};
  message = "";
  try {
    const created = await coffees.create({
      name,
      roaster,
      country,
      region,
      producer,
      process,
      harvest_year: harvestYear ? Number(harvestYear) : null,
      roast_level: roastLevel,
      is_decaf: isDecaf,
      notes,
    });
    await goto(`/coffees/${created.id}/`);
  } catch (error) {
    ({ fields: errors, message } = toFormErrors(error));
  } finally {
    busy = false;
  }
}
</script>

<h1>Add a coffee</h1>
<p class="muted">
  Only the name is required. Fill in what you know now and edit it later.
</p>

<form onsubmit={submit}>
  <Field label="Name" error={errors.name}>
    <input bind:value={name} required placeholder="Yirgacheffe Kochere" />
  </Field>

  <ReferencePicker kind="roasters" label="Roaster" bind:value={roaster} error={errors.roaster} />

  <ReferencePicker
    kind="countries"
    label="Country of origin"
    bind:value={country}
    allowCreate={false}
    hint="From the ISO country list."
    error={errors.country}
    onselect={() => {
      // A region belongs to a country, so changing the country invalidates it.
      region = null;
    }}
  />

  <ReferencePicker
    kind="regions"
    label="Region"
    bind:value={region}
    searchWith={{ country }}
    createWith={{ country }}
    hint={country ? undefined : "Pick a country first to add a new region."}
    allowCreate={country !== null}
    error={errors.region}
  />

  <ReferencePicker kind="producers" label="Farm or producer" bind:value={producer} error={errors.producer} />
  <ReferencePicker kind="processes" label="Process" bind:value={process} error={errors.process} />

  <Field label="Harvest year" error={errors.harvest_year}>
    <input type="number" bind:value={harvestYear} min="1900" max="2100" placeholder="2025" />
  </Field>

  <Field label="Roast level" error={errors.roast_level}>
    <select bind:value={roastLevel}>
      <option value="">Not recorded</option>
      <option value="light">Light</option>
      <option value="medium_light">Medium-light</option>
      <option value="medium">Medium</option>
      <option value="medium_dark">Medium-dark</option>
      <option value="dark">Dark</option>
    </select>
  </Field>

  <label class="inline">
    <input type="checkbox" bind:checked={isDecaf} />
    <span>Decaffeinated</span>
  </label>

  <Field label="Notes" error={errors.notes}>
    <textarea bind:value={notes} rows="3"></textarea>
  </Field>

  {#if message}<p class="field-error">{message}</p>{/if}

  <button type="submit" disabled={busy}>{busy ? "Saving…" : "Save coffee"}</button>
</form>

<style>
  .inline {
    display: flex;
    align-items: center;
    gap: var(--gap-sm);
  }

  .inline input {
    width: auto;
  }

  .inline span {
    margin: 0;
    color: var(--text);
  }
</style>
