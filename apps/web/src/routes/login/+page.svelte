<script lang="ts">
import { goto } from "$app/navigation";
import { page } from "$app/state";
import { toFormErrors } from "$lib/api/errors";
import { auth } from "$lib/stores/auth.svelte";

let email = $state("");
let password = $state("");
let errors = $state<Record<string, string>>({});
let message = $state("");
let busy = $state(false);

async function submit(event: SubmitEvent) {
  event.preventDefault();
  busy = true;
  errors = {};
  message = "";
  try {
    await auth.login(email, password);
    // Only ever a path from our own URL, so this cannot redirect off-site.
    const next = page.url.searchParams.get("next");
    await goto(next?.startsWith("/") ? next : "/");
  } catch (error) {
    ({ fields: errors, message } = toFormErrors(error));
  } finally {
    busy = false;
  }
}
</script>

<main>
  <h1>Sign in</h1>

  <form onsubmit={submit} class="stack">
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
        autocomplete="current-password"
      />
      {#if errors.password}<p class="field-error">{errors.password}</p>{/if}
    </label>

    {#if message}<p class="field-error">{message}</p>{/if}

    <button type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
  </form>

  <p class="muted">No account? <a href="/register/">Register</a></p>
</main>
