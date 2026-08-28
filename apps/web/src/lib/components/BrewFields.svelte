<script lang="ts">
import type { Grinder } from "$lib/api/types";
import Field from "./Field.svelte";

/**
 * The method-aware part of the brew form.
 *
 * Which inputs appear, in what order, and which are required all come from
 * the chosen method's `parameter_schema`. Espresso shows a yield; pour over
 * shows a bloom. Adding a brew method server-side is a fixture change, and
 * this component picks it up with no edit here.
 */
export interface BrewValues {
  dose_grams: string;
  water_grams: string;
  water_temp_c: string;
  grinder: string;
  grind_setting: string;
  grind_microns: string;
  total_time_seconds: string;
  bloom_time_seconds: string;
  bloom_water_grams: string;
  pressure_bar: string;
  yield_grams: string;
}

interface Props {
  values: BrewValues;
  schema: { fields?: string[]; required?: string[] } | null;
  grinders: Grinder[];
  errors: Record<string, string>;
}

let { values = $bindable(), schema, grinders, errors }: Props = $props();

const LABELS: Record<keyof BrewValues, string> = {
  dose_grams: "Coffee (g)",
  water_grams: "Water (g)",
  water_temp_c: "Water temperature (°C)",
  grinder: "Grinder",
  grind_setting: "Grind setting",
  grind_microns: "Grind size (microns)",
  total_time_seconds: "Total time (seconds)",
  bloom_time_seconds: "Bloom time (seconds)",
  bloom_water_grams: "Bloom water (g)",
  pressure_bar: "Pressure (bar)",
  yield_grams: "Yield (g)",
};

const NUMERIC = new Set<keyof BrewValues>([
  "dose_grams",
  "water_grams",
  "water_temp_c",
  "grind_microns",
  "total_time_seconds",
  "bloom_time_seconds",
  "bloom_water_grams",
  "pressure_bar",
  "yield_grams",
]);

// Fall back to the common set when a method declares no schema, so a custom
// method is still usable rather than showing an empty form.
const FALLBACK = ["dose_grams", "water_grams", "water_temp_c", "grinder", "grind_setting"];

const fields = $derived(
  (schema?.fields?.length ? schema.fields : FALLBACK).filter(
    (f): f is keyof BrewValues => f in LABELS,
  ),
);
const required = $derived(new Set(schema?.required ?? []));
</script>

{#each fields as field (field)}
  {#if field === "grinder"}
    <Field label={LABELS[field]} error={errors[field]}>
      <select bind:value={values.grinder}>
        <option value="">Not recorded</option>
        {#each grinders as grinder (grinder.id)}
          <option value={grinder.id}>{grinder.name}</option>
        {/each}
      </select>
    </Field>
  {:else if NUMERIC.has(field)}
    <Field label={LABELS[field] + (required.has(field) ? " *" : "")} error={errors[field]}>
      <input
        type="number"
        step="0.1"
        min="0"
        bind:value={values[field]}
        required={required.has(field)}
      />
    </Field>
  {:else}
    <Field
      label={LABELS[field] + (required.has(field) ? " *" : "")}
      error={errors[field]}
      hint={field === "grind_setting"
        ? "Whatever your grinder shows: 3, 12 clicks, medium-fine."
        : undefined}
    >
      <input bind:value={values[field]} required={required.has(field)} />
    </Field>
  {/if}
{/each}
