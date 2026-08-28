<script lang="ts">
import { goto } from "$app/navigation";
import { toFormErrors } from "$lib/api/errors";
import { auth } from "$lib/stores/auth.svelte";

let email = $state("");
let password = $state("");
let displayName = $state("");
let errors = $state<Record<string, string>>({});
let message = $state("");
let busy = $state(false);

async function submit(event: SubmitEvent) {
  event.preventDefault();
  busy = true;
  errors = {};
  message = "";
  try {
    await auth.register(email, password, displayName);
    await goto("/");
  } catch (error) {
    ({ fields: errors, message } = toFormErrors(error));
  } finally {
    busy = false;
  }
}
</script>

<main>
  <h1>Create an account</h1>

  <form onsubmit={submit} class="stack">
    <label>
      <span>Display name</span>
      <input bind:value={displayName} autocomplete="nickname" />
      {#if errors.display_name}<p class="field-error">{errors.display_name}</p>{/if}
    </label>

    <label>
      <span>Email</span>
      <input type="email" bind:value={email} required autocomplete="email" />
      {#if errors.email}<p class="field-error">{errors.email}</p>{/if}
    </label>

    <label>
      <span>Password</span>
      <input
        type="password"
        bind:value={password}
        required
        autocomplete="new-password"
      />
      {#if errors.password}<p class="field-error">{errors.password}</p>{/if}
      <p class="muted">At least 10 characters, and not too similar to your email.</p>
    </label>

    {#if message}<p class="field-error">{message}</p>{/if}

    <button type="submit" disabled={busy}>{busy ? "Creating…" : "Create account"}</button>
  </form>

  <p class="muted">Already registered? <a href="/login/">Sign in</a></p>
</main>
