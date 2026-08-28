/**
 * Form value normalisation.
 *
 * Svelte binds `<input type="number">` to a number (or null when blank) and
 * text inputs to strings, so both shapes reach a submit handler. Sending the
 * wrong one is easy to miss: it does not fail a typecheck when the state is
 * initialised with `""`, and it only surfaces in a browser.
 */
export type FormValue = string | number | null | undefined;

/**
 * A value ready for the API, or null when it was left blank.
 *
 * Blank must be null rather than 0: unrecorded is not the same as zero, and the
 * API distinguishes them.
 */
export function toApiNumber(value: FormValue): string | number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  return value.trim() === "" ? null : value;
}

/** A text value ready for the API. Blank stays blank, never null. */
export function toApiText(value: FormValue): string {
  if (value === null || value === undefined) return "";
  return String(value);
}
