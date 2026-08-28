<script lang="ts">
interface Props {
  label: string;
  error?: string | undefined;
  hint?: string | undefined;
  children: import("svelte").Snippet;
}

let { label, error, hint, children }: Props = $props();
</script>

<label>
  <span>{label}</span>
  {@render children()}
  {#if hint}<span class="hint">{hint}</span>{/if}
  {#if error}<p class="field-error">{error}</p>{/if}
</label>

<style>
  .hint {
    font-size: 0.8125rem;
    color: var(--text-muted);
    margin-top: 0.25rem;
  }
</style>
