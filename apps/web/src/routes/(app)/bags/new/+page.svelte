<script lang="ts">
import { goto } from "$app/navigation";
import { page } from "$app/state";
import { toFormErrors } from "$lib/api/errors";
import { bags, coffees } from "$lib/api/resources";
import type { Coffee } from "$lib/api/types";
import Field from "$lib/components/Field.svelte";
import ReferencePicker from "$lib/components/ReferencePicker.svelte";

// Arriving from a coffee page preselects it; arriving from the nav does not.
const presetCoffee = page.url.searchParams.get("coffee");

let coffeeId = $state(presetCoffee ?? "");
let purchasedFrom = $state<string | null>(null);
let purchaseDate = $state(new Date().toISOString().slice(0, 10));
let roastDate = $state("");
let weight = $state("");
let priceAmount = $state("");
let priceCurrency = $state("");
let notes = $state("");

let errors = $state<Record<string, string>>({});
let message = $state("");
let busy = $state(false);

const coffeeOptions = coffees.list<Coffee>({ page_size: 100 });

async function submit(event: SubmitEvent) {
  event.preventDefault();
  busy = true;
  errors = {};
  message = "";
  try {
    const created = await bags.create({
      coffee: coffeeId,
      purchased_from: purchasedFrom,
      purchase_date: purchaseDate || null,
      roast_date: roastDate || null,
      weight_grams: weight || null,
      price_amount: priceAmount || null,
      price_currency: priceCurrency || "",
      notes,
    });
    await goto(`/bags/${created.id}/`);
  } catch (error) {
    ({ fields: errors, message } = toFormErrors(error));
  } finally {
    busy = false;
  }
}
</script>

<h1>Record a purchase</h1>

<form onsubmit={submit}>
  <Field label="Coffee" error={errors.coffee}>
    {#await coffeeOptions then list}
      <select bind:value={coffeeId} required>
        <option value="" disabled>Choose a coffee…</option>
        {#each list.results as coffee (coffee.id)}
          <option value={coffee.id}>{coffee.name}</option>
        {/each}
      </select>
      {#if list.results.length === 0}
        <p class="muted">
          No coffees yet — <a href="/coffees/new/">add one first</a>.
        </p>
      {/if}
    {/await}
  </Field>

  <ReferencePicker
    kind="roasters"
    label="Bought from"
    bind:value={purchasedFrom}
    hint="The cafe or shop, which is often not the roaster."
    error={errors.purchased_from}
  />

  <Field label="Purchase date" error={errors.purchase_date}>
    <input type="date" bind:value={purchaseDate} />
  </Field>

  <Field label="Roast date" error={errors.roast_date} hint="Freshness is per bag.">
    <input type="date" bind:value={roastDate} />
  </Field>

  <Field label="Weight (grams)" error={errors.weight_grams}>
    <input type="number" bind:value={weight} min="1" step="1" placeholder="250" />
  </Field>

  <div class="pair">
    <Field label="Price" error={errors.price_amount}>
      <input type="number" bind:value={priceAmount} min="0" step="0.01" />
    </Field>
    <Field label="Currency" error={errors.price_currency}>
      <input bind:value={priceCurrency} maxlength="3" placeholder="AUD" />
    </Field>
  </div>

  <Field label="Notes" error={errors.notes}>
    <textarea bind:value={notes} rows="3"></textarea>
  </Field>

  {#if message}<p class="field-error">{message}</p>{/if}

  <button type="submit" disabled={busy || !coffeeId}>
    {busy ? "Saving…" : "Save bag"}
  </button>
</form>

<style>
  .pair {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: var(--gap);
  }
</style>
