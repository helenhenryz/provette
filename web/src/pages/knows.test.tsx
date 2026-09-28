/* Rules: how the rules are chosen is said above them; a rule added on this site can be deleted
   (asked once, in place), and a shipped one cannot; a word added on this site can be taken out,
   and the shipped words have no ×. "Proposed" says what it means on hover. */

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { KnowsPage } from "./Knows";

const calls = vi.hoisted(() => ({
  removed: [] as string[],
  words: [] as string[],
}));
const shipped = {
  rule_id: "NO-SAMPLE-INTO-REAGENT-WELL",
  family: 1,
  tier: "role",
  title: "A tip that had been in a sample went into a reagent",
  description: "d",
  status: "proposed" as const,
  proposed_by: "Helen Henry and Nyle Hussain",
};
const added = {
  ...shipped,
  rule_id: "TEST-RULE",
  title: "A test rule",
  proposed_by: "a judge",
};
const file = (r: typeof shipped, removable: boolean) => ({
  id: r.rule_id,
  file: `${r.rule_id}.yaml`,
  shape: "no_carry_over",
  title: r.title,
  severity: "warning",
  why: "w",
  fix: "f",
  sources: [],
  proposed_by: r.proposed_by,
  status: "proposed",
  adopted_on: null,
  removable,
});
const lists = { reagent: ["master mix", "lysozyme"], sample: ["sample"] };

vi.mock("../lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("../lib/api")>();
  return {
    ...real,
    judge: { get: () => "key", requestUnlock: () => Promise.resolve(true) },
    api: {
      ...real.api,
      rules: () =>
        Promise.resolve({ schema_version: 1, rules: [shipped, added] }),
    },
    outcomes: {
      ...real.outcomes,
      all: () => Promise.resolve({ records: [], failures: [] }),
    },
    coverageTechniques: () => Promise.resolve({ techniques: [], source: null }),
    roles: {
      get: () =>
        Promise.resolve({
          lists,
          list_names: ["reagent", "sample"],
          added_here: { reagent: ["lysozyme"], sample: [] },
        }),
      add: vi.fn(),
      remove: (list: string, word: string) => {
        calls.words.push(`${list}:${word}`);
        return Promise.resolve({
          lists: { ...lists, reagent: ["master mix"] },
          list_names: ["reagent", "sample"],
          added_here: { reagent: [], sample: [] },
          removed: { list, word },
        });
      },
    },
    declared: {
      ...real.declared,
      list: () =>
        Promise.resolve({
          rules: [file(shipped, false), file(added, true)],
          shapes: [],
        }),
      remove: (id: string) => {
        calls.removed.push(id);
        return Promise.resolve({ deleted: id, rules_loaded: [] });
      },
    },
  };
});

function page(hash = "") {
  return render(
    <MemoryRouter initialEntries={[`/rules${hash}`]}>
      <KnowsPage />
    </MemoryRouter>,
  );
}

describe("KnowsPage", () => {
  beforeEach(() => {
    calls.removed = [];
    calls.words = [];
  });

  it("says how rules are chosen, and deletes only a rule added on this site", async () => {
    page();
    expect(
      await screen.findByText(
        /Every rule runs on every protocol; each speaks only when/,
      ),
    ).toBeInTheDocument();
    const tag = screen.getAllByText(/proposed by/)[0];
    expect(tag.closest("[title]")).toHaveAttribute(
      "title",
      "runs on every check; its findings are notes until adopted in the file",
    );
    // the shipped rule has no delete; the added one has, asked once in place
    const shippedRow = screen
      .getByText("NO-SAMPLE-INTO-REAGENT-WELL")
      .closest("li")!;
    await userEvent.click(within(shippedRow).getByText(shipped.title));
    expect(within(shippedRow).queryByText("Delete this rule")).toBeNull();
    const addedRow = screen.getByText("TEST-RULE").closest("li")!;
    await userEvent.click(within(addedRow).getByText("A test rule"));
    await userEvent.click(within(addedRow).getByText("Delete this rule"));
    expect(
      within(addedRow).getByText(/stops running from the next check/),
    ).toBeInTheDocument();
    await userEvent.click(
      within(addedRow).getByRole("button", { name: "Delete" }),
    );
    expect(calls.removed).toEqual(["TEST-RULE"]);
    expect(screen.queryByText("TEST-RULE")).toBeNull();
  });

  it("takes out a word added on this site; a shipped word has no ×", async () => {
    page("#words");
    // the first list, reagent, is open when the tab opens
    expect(await screen.findByText("added on this site")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Take master mix out/ }),
    ).toBeNull();
    await userEvent.click(
      screen.getByRole("button", {
        name: "Take lysozyme out of the reagent list",
      }),
    );
    expect(calls.words).toEqual(["reagent:lysozyme"]);
    expect(screen.queryByText("added on this site")).toBeNull();
  });
});
