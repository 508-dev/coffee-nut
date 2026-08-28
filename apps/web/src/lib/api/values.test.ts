import { describe, expect, it } from "vitest";
import { toApiNumber, toApiText } from "./values";

describe("toApiNumber", () => {
  it("passes numbers through", () => {
    // Svelte binds type="number" inputs to numbers, which is what broke the
    // brew form: the original helper called .trim() on them.
    expect(toApiNumber(14)).toBe(14);
    expect(toApiNumber(0)).toBe(0);
  });

  it("treats a blank field as unrecorded, not zero", () => {
    expect(toApiNumber(null)).toBeNull();
    expect(toApiNumber(undefined)).toBeNull();
    expect(toApiNumber("")).toBeNull();
    expect(toApiNumber("   ")).toBeNull();
  });

  it("keeps numeric strings as strings", () => {
    // Decimals are strings on the wire, so "14.0" must not become 14.
    expect(toApiNumber("14.0")).toBe("14.0");
  });

  it("rejects NaN rather than sending it", () => {
    expect(toApiNumber(Number.NaN)).toBeNull();
    expect(toApiNumber(Number.POSITIVE_INFINITY)).toBeNull();
  });
});

describe("toApiText", () => {
  it("never returns null", () => {
    expect(toApiText(null)).toBe("");
    expect(toApiText(undefined)).toBe("");
  });

  it("stringifies a number from a coerced input", () => {
    expect(toApiText(3)).toBe("3");
  });
});
