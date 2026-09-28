import type { DeclaredRuleData } from "./api";

/* The words for the roles and lists a declared rule names, shared by the rule form and the
   rules page so a rule reads the same in both. */
export const ROLE_WORDS: Record<string, string> = {
  sample: "a sample",
  reagent: "a reagent",
  carrier: "a carrier (water, buffer, medium)",
  any: "anything",
  stock: "a stock (a tube the protocol draws from)",
  sample_well: "a well that holds a sample",
  reagent_well: "a well that holds a reagent",
  add_first: "a diluent or buffer (the add-first list)",
  add_last: "an enzyme or mix (the add-last list)",
};

const w = (v: unknown): string =>
  typeof v === "string" ? (ROLE_WORDS[v] ?? v) : String(v);

/* The rule as one sentence, filled from its own fields: "an enzyme or mix must go in after a
   diluent or buffer", never the shape's template with the blanks left in. */
export function ruleSentence(
  r: Pick<DeclaredRuleData, "shape"> & Record<string, unknown>,
): string {
  if (r.shape === "no_carry_over")
    return `a tip that touched ${w(r.carried_role)} must never go into ${w(r.into_role)}`;
  if (r.shape === "full_well_not_mixed")
    return `a well more than ${String(r.share)} full must not be mixed with a stroke of more than ${String(r.stroke_share)} of its volume`;
  const half = r.half_clause
    ? `, and only when the well held less than ${String(r.share)} of its final diluent`
    : "";
  return `${w(r.last)} must go in after ${w(r.first)}${half}`;
}
