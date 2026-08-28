import { ApiError } from "./client";

/**
 * Turn any thrown value into something a form can render.
 *
 * Returns per-field messages plus a single form-level message, matching the
 * API's error envelope where `field: null` means "not about one input".
 */
export function toFormErrors(error: unknown): {
  fields: Record<string, string>;
  message: string;
} {
  if (error instanceof ApiError) {
    const formLevel = error.body.errors.find((e) => e.field === null);
    return {
      fields: error.fieldErrors(),
      message: formLevel?.message ?? error.body.detail,
    };
  }
  return { fields: {}, message: "Something went wrong. Please try again." };
}
