/**
 * Hand-picked aliases over the generated schema.
 *
 * Components import from here rather than reaching into `schema.d.ts`, so a
 * backend rename shows up as one broken alias instead of a broken component.
 */
import type { components } from "./schema";

type Schemas = components["schemas"];

export type User = Schemas["User"];
export type Coffee = Schemas["Coffee"];
export type Bag = Schemas["Bag"];
export type Brew = Schemas["Brew"];
export type Grinder = Schemas["Grinder"];
export type BrewMethod = Schemas["BrewMethod"];
export type Country = Schemas["Country"];
export type Roaster = Schemas["Roaster"];
export type TastingNote = Schemas["TastingNote"];
export type PublicBrew = Schemas["PublicBrew"];

/** Cursor-paginated list, used by brews, coffees, and bags. */
export interface Paginated<T> {
  next: string | null;
  previous: string | null;
  results: T[];
  count?: number;
}
