<script lang="ts">
import { goto } from "$app/navigation";
import { toFormErrors } from "$lib/api/errors";
import { grinders as grindersApi, updateMe } from "$lib/api/resources";
import type { Grinder } from "$lib/api/types";
import Field from "$lib/components/Field.svelte";
import { auth } from "$lib/stores/auth.svelte";

let displayName = $state(auth.user?.display_name ?? "");
let units = $state(auth.user?.profile?.preferred_units ?? "metric");
let saved = $state(false);
let errors = $state<Record<string, string>>({});
let message = $state("");
let busy = $state(false);

let grinders = $state<Grinder[]>([]);
let newGrinder = $state("");
let grinderError = $state("");

const loadGrinders = (async () => {
  const page = await grindersApi.list<Grinder>({ page_size: 50 });
  grinders = page.results;
})();

async function saveProfile(event: SubmitEvent) {
  event.preventDefault();
  busy = true;
  saved = false;
  errors = {};
  message = "";
  try {
    auth.user = await updateMe({
      display_name: displayName,
      profile: { preferred_units: units },
    });
    saved = true;
  } catch (error) {
    ({ fields: errors, message } = toFormErrors(error));
  } finally {
    busy = false;
  }
}

async function addGrinder(event: SubmitEvent) {
  event.preventDefault();
  grinderError = "";
  try {
    const created = await grindersApi.create({ name: newGrinder });
    grinders = [...grinders, created];
    newGrinder = "";
  } catch (error) {
    grinderError = toFormErrors(error).fields.name ?? toFormErrors(error).message;
  }
}

async function removeGrinder(id: string) {
  await grindersApi.remove(id);
  grinders = grinders.filter((g) => g.id !== id);
}

async function signOut() {
  await auth.logout();
  await goto("/login/");
}
</script>

<h1>Settings</h1>

<form onsubmit={saveProfile}>
  <Field label="Display name" error={errors.display_name}>
    <input bind:value={displayName} />
  </Field>

  <Field
    label="Preferred units"
    error={errors.profile}
    hint="Display only. The API always speaks grams and Celsius."
  >
    <select bind:value={units}>
      <option value="metric">Metric</option>
      <option value="imperial">Imperial</option>
    </select>
  </Field>

  {#if message}<p class="field-error">{message}</p>{/if}

  <button type="submit" disabled={busy}>{busy ? "Saving…" : "Save"}</button>
  {#if saved}<span class="saved muted">Saved</span>{/if}
</form>

<section>
  <h2>Grinders</h2>
  <p class="muted">
    Settings mean nothing across machines, so recording which grinder you used is
    what makes "fineness 3" comparable to your own past brews.
  </p>

  {#await loadGrinders then}
    <ul class="plain">
      {#each grinders as grinder (grinder.id)}
        <li>
          {grinder.name}
          <button type="button" class="secondary" onclick={() => removeGrinder(grinder.id)}>
            Remove
          </button>
        </li>
      {/each}
    </ul>
  {/await}

  <form onsubmit={addGrinder} class="add">
    <input bind:value={newGrinder} placeholder="Comandante C40" required />
    <button type="submit">Add</button>
  </form>
  {#if grinderError}<p class="field-error">{grinderError}</p>{/if}
</section>

<section>
  <h2>Account</h2>
  <p class="muted">{auth.user?.email}</p>
  <button type="button" class="secondary" onclick={signOut}>Sign out</button>
</section>

<style>
  .saved {
    margin-left: var(--gap-sm);
    font-size: 0.875rem;
  }

  h2 {
    font-size: 1rem;
    margin-top: var(--gap-lg);
  }

  .plain {
    list-style: none;
    padding: 0;
  }

  .plain li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--gap);
    padding: 0.25rem 0;
  }

  .add {
    display: flex;
    gap: var(--gap-sm);
  }
</style>
