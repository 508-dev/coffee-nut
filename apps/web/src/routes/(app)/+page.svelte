<script lang="ts">
import { auth } from "$lib/stores/auth.svelte";
</script>

<h1>Hello, {auth.user?.display_name || auth.user?.email}</h1>
<p class="muted">
  Feature screens land in the next pass. The API is complete; see
  <code>/api/docs/</code>.
</p>
