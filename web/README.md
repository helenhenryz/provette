# `web/` — the product's pages

React with TypeScript, built by Vite into static files the API serves. One typeface, a dozen
tokens, components with one job each, no inline styles, and every number with its unit. What
the pages are and why: [`docs/how-it-works.md`](../docs/how-it-works.md), section 9; how they
look, read and behave: [`docs/design.md`](../docs/design.md); why this stack:
[`docs/deploy.md`](../docs/deploy.md), "The stack behind the pages".

```
npm ci                 once
npm run dev            Vite on :5173, proxying /api to the API on :8765 (deploy/dev-api.sh)
npm run lint           oxlint (.oxlintrc.json)
npm run build          web/dist, what the image and deploy/dev-api.sh serve
npx vitest run         the rendering tests (make check-web runs all four)
```

`VITE_REPOSITORY=https://github.com/<owner>/provette npm run build` puts the source link in the
sidebar and on the About page; without it the pages show no link.

## Layout

```
src/tokens.css          the design tokens: colour (light and dark), space, type, radius
src/base.css            reset, typography, the few shared utility classes
src/routes.tsx          the routes (below); src/main.tsx mounts them
src/lib/api.ts          the one typed contract with the backend, and the fetchers
src/lib/format.ts       numbers and words, always with a unit
src/lib/plate.ts        what a plate grid shows, from the map, the verify report and the replay
src/lib/replayState.ts  the replay's state at a position, rebuilt from the export's deltas
src/lib/rules.ts        the words for roles and lists, shared by the rule form and the rules page
src/lib/verdict.ts      the verifier's findings in its own wording
src/lib/wells.ts        well names as a person writes them ("A1–A12, B1–B6 in slot 2")
src/lib/theme.ts        light, dark or the system's choice, remembered per browser
src/lib/useFetch.ts     fetch once per key; a page renders loading, error or data
src/components/         one job each, a .module.css beside each
src/pages/              one route each; a page composes components and fetches through lib/api.ts
src/replay/             the deck replay: 2D plate, 3D deck (react-three-fiber), a clock, a scrubber
src/test/               the test setup and the frozen fixtures (tests/web/fixtures)
```

## Routes

| route | page | what it is |
|---|---|---|
| `/` | `Home` | the composer: write a request, then Plan, then Run, on one evolving page |
| `/plan/:id` | `Plan` | the plate map proposed for a request, editable well by well, with each well's sum; approve it |
| `/examples` | `Gallery` | the evaluation's agent runs as examples, grouped by request, a row per model |
| `/runs/:id` | `RunResult` | a live run as it happens and, when it ends, its run record |
| `/episodes/:set/:condition/:requestId` | `Episode` | a pre-run episode's run record |
| `/check`, `/check/:id` | `Check`, `CheckResult` | paste or upload a protocol (and a map) and get its run record, at a shareable URL; `/check` opens the tab's last check when one is remembered, `/check?new` the composer |
| `/rules`, `/rules/new` | `Knows`, `RuleForm` | Rules: Rules, Words, Coverage, Failures; and the rule form, a sentence with blanks |
| `/methods` | `How` | the methods page: the numbers behind the runs, computed from `eval/` |
| `/docs/:name` | `Doc` | the rulebook and what it links to, rendered from `docs/` |
| `/about` | `About` | what it is, what it is not, the team, the licence |

Any other address is the not-found page.

## The components

| component | job | renders generically? |
|---|---|---|
| `Shell`, `History` | the sidebar that holds everything (New run, Check a protocol, Examples, Rules, Methods, About, the history of this deployment's runs, plans and checks with a ⋯ menu each, and at its foot the version, the judge unlock and Settings); a drawer and a slim bar on phones | |
| `vocabulary` (`Badge`, `Lozenge`, `Tabs`, ...) | the component vocabulary (`docs/how-it-works.md`, section 9): a status word, a severity, a tab strip | |
| `RunRecord` | the run record as one screen: header, stage (Replay · Plate map · Protocol · Prep sheet), the checks rail, findings, teaching cards | |
| `Timeline` | the loop as it happens: every tool call a row, each draft followed by the checker's verdict | **yes**: a new tool is a row with its title |
| `ChecksList` | the rail's checks: simulator, plate map, each rule, with "not checked" as a state | |
| `Findings` | what the rules found | **yes**: any finding with rule id, severity, title, explanation, fix, line |
| `CodeReview`, `CodeView` | the protocol with findings beside the lines; the source with marked lines | |
| `PlateGrid`, `PlateFromMap` | the plate as a plate: what each well should hold and does hold; the map drawn with the replay's close-up | reads `intent.wells` when the API has it |
| `PlateMapEditor`, `PlateMapSums` | the proposal, editable well by well or as JSON; each well's contents as a sum | |
| `PrepSheet` | what to load where, from the verify report | **yes**: every prep line and tip row |
| `UnplacedLiquids` | "I do not know what 'lysozyme' is": one card per unplaced liquid, five answers, written to the word lists | |
| `OutcomeForm` | the failed-run record: "did this run work?" and two sentences when it did not | |
| `EpisodeCard`, `RunGroup` | one episode in the gallery; one request with its runs as rows | |
| `Settings` | the Settings dialog: the theme, and the run and plan budgets with Reset to defaults | |
| `Notice` | a sentence in a box | |
| `replay/Replay` | the deck replay: `Deck2D`, `Deck3D`, `Controls`, driven by `clock.ts` over `timeline.ts`; `index.ts` says how a page uses it | |

## Where an extension goes

* **A new finding field, prep column or step field** the page should show: the generic renderer
  in the component above, one line.
* **A new tool in the agent**: nothing here; the API's `steps.py` names it.
* **A new page**: `src/pages/<Name>.tsx`, a route in `src/routes.tsx`, an entry in `Shell`'s `PLACES`.
* **A new number from `eval/`**: `api/evidence.py` computes it, `src/pages/How.tsx` says it.
* **A new colour or size**: `src/tokens.css`, both themes (`docs/design.md`).
* **A new declared-rule shape**: its sentence in `src/pages/RuleForm.tsx`; the fields come from
  the API.

## Tests

`src/components/*.test.tsx` render the components and pages on the frozen episode files in
`tests/web/fixtures/` (the API's own answers for one episode of the agent runs; refresh with
`make web-fixtures` and read the diff); `src/lib/plate.test.ts` checks the plate logic against
the same files; `src/replay/*.test.ts` check the replay's state, timeline and scene as numbers,
and `perf.test.ts` its frame cost on the largest analysis it is given (`PROVETTE_BIG_REPLAY`).
