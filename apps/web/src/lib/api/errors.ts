import { ApiError, NetworkError } from "./client";

/**
 * Turn a failed request into something a form can render.
 *
 * Only two things are expected here: an `ApiError` the server sent, and a
 * `NetworkError` when the request could not be sent. Anything else is a bug in
 * our own code and is rethrown rather than shown as "something went wrong" —
 * swallowing it would let a real defect masquerade as a validation failure and
 * silently pass a browser test.
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

  if (error instanceof NetworkError) {
    return { fields: {}, message: "Could not reach the server. Check your connection." };
  }

  throw error;
}
