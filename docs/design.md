# How Provette looks, reads and behaves

The product is used by a working lab scientist: someone who runs an OT-2 and knows what a plate
map, a master mix, a tip rack and a µl are. Every page is held against one question: **would an
OT-2 user be worse off if this line vanished?** If not, it goes; if the fact matters, it becomes a
hover, a fold or a state. The explanations a newcomer needs live in `docs/`, where the two of us
maintain them, not on the pages.

## The principles, with their sources

1. **People scan; halve the words.** Most readers scan a new page; concise, scannable, objective
   text measured more than twice as usable. (Nielsen, *How Users Read on the Web*, 1997)
2. **A fifth of the text gets read.** A screen whose job is one action carries well under 120
   words above the fold. (Nielsen, *How Little Do Users Read?*, 2008)
3. **Progressive disclosure, two levels at most.** The few important things first, the rest on
   request, never three levels deep. (Nielsen, *Progressive Disclosure*, 2006)
4. **The first two words of a line carry it.** Headings say what their section holds.
   (Pernice, *F-Shaped Pattern*, 2017; *The Layer-Cake Pattern of Scanning*, 2019)
5. **A label is one to four words; a tooltip holds only what a reader would look up, never what a
   task needs.** (Grafana, *UX writing*; Kendrick, *Tooltip Guidelines*, NN/g 2019)
6. **Recognition over recall.** A link's label carries the scent, not a sentence around it.
   (Nielsen, *10 Usability Heuristics*; NN/g, *Information Scent*)
7. **Short sentences, no filler, say a thing once.** Under 20 words, keywords first.
   (Loranger and Nielsen, *Microcontent*, 2017)
8. **Density through numbers and hover, not prose.** An empty state is one line. (Grafana,
   *Dashboard best practices*; Kaplan, *Empty State Interface Design*, NN/g 2021)

## What never goes

* **Every number, with its unit.** `lib/format.ts` writes them; a bare number is a bug.
* **The honest words, as they are:** "Not checked" as its own row, "not verified", "the simulator
  rejected the protocol, so nothing else was checked", "No rule fired on this protocol.", and
  "Provette checks the logic of a protocol, not the physics." (said in full on About, and as the
  physics line inside Not checked).
* **What a task needs stays on the page:** a form's hints are placeholders or the field's own
  caption, never a tooltip.
* **Every result a page shows is computed from a file**, and says which (Methods: "Computed from
  n files under eval/"; About reads the same numbers). A number is never typed into a page.

## The frame: a chat app's

One sidebar holds everything, as people know it from chat apps: **New run** first, then **Check a
protocol**, the reading pages (**Examples, Rules, Methods, About**), then the **History** of this
deployment, newest first, one line each with a status dot, and at the foot the version, the judge
key and **Settings**. A page has no bar on a desktop. On a phone the sidebar is a drawer, closed
with the × on the left of the name, and a slim bar carries the menu, the name and a new run.

* **A history line** has a ⋯ menu on hover (always on a touch screen): **Pin** (kept in this
  browser) and **Delete**, which asks in a dialog first.
* **Settings** is a dialog: sections on the left, rows of "what it is · the control" on the right,
  Save and Reset to defaults pinned at the foot. A number field shows its range under the box and,
  when changed, a ↺ back to its default.
* **A dialog** dims and blurs the page, has one clear primary button (red for a delete), closes on
  Escape and on a click outside.

## The tokens

`web/src/tokens.css` holds every colour, size and space, for the light and the dark theme; nothing
else in the code names a colour. `web/src/base.css` holds the reset, the type and the few shared
classes (`.btn`, `.btn.primary`, `.btn.ghost`, `.btn.lg`, `.field`, `.stack`, `.muted`, `.faint`,
`.mono`, `.num` for tabular numbers).

| token | values |
|---|---|
| type | `--t-1` 12 px small print · `--t-2` 13 px meta and tables · `--t-3` 15 px body · `--t-4` 17 px lead · `--t-5` 22 px h2 · `--t-6` 28 px h1 · `--t-7` 36 px display |
| space | `--s-1` 4 px to `--s-8` 64 px |
| radius | `--radius` 6 px · `--radius-lg` 10 px · `--radius-xl` 14 px |
| controls | `--control` 36 px; `--control-lg` 44 px, the page's one primary action |
| width | `--measure` 68 characters for prose; `--page` 1,120 px |
| colour | `--bg`, `--surface`, `--surface-2`, `--raised`, `--border`, `--border-strong`, `--text`, `--muted`, `--faint`, `--link`, and the states `--verified`, `--error`, `--warning`, `--note`, each with its `-bg` |
| depth | `--shadow` (a card), `--shadow-lg` (the composer, a dialog), `--hairline` (the lit top edge of a raised surface), `--glow` and `--glow-2` (the accent's and the link's halo), `--stage-hi` and `--stage-lo` (the replay's stage, centre and edge; the 3D scene reads them too) |

Inter for text and JetBrains Mono for code, both bundled (`@fontsource-variable`). Python in a code
view is coloured by `lib/highlight.tsx` from the `--code-*` tokens.

**Dark is the default.** It is built in layers: the page (`--bg`) is the darkest, a card or the
sidebar (`--surface`, `--raised`) sits a step lighter with a hairline of light on its top edge,
and a control on it (`--surface-2`) a step lighter again. The one accent is the green of
`--verified`: the primary button, the page you are on in the sidebar, the play button, a chosen
filter and the brand mark, each with a faint halo (`--glow`). Two halos at the top of every page
and a field of wells behind the home page's greeting are decoration; they carry no word and no
number. The 3D replay stands on a floor grid under a key light that casts shadows and a blue rim
light from behind (`replay/Deck3D.tsx`, `Lights` and `Floor`): convention, like the rest of its
shading, and nothing it shows is physics.

## The patterns every page reuses

`web/src/components/vocabulary.tsx` is the vocabulary; a page composes it rather than inventing.

| pattern | what it is for |
|---|---|
| `Badge` | the verdict word: Verified, Not verified, Running, Checked; its sentence in a popover |
| `Lozenge` | a finding's severity: error, warning, note |
| `Tag`, `Chip` | a static word in a pill; a filter with its count |
| `Tabs`, `Segments` | a tab strip with counts; a two- or three-way switch |
| `Fold` | a section that opens on request, with a one-line hint of what is inside |
| `Row`, `Rail`, `RailSection` | the run record's right-hand checks, one row per check |
| `Stage` | the one large area of a record: Replay, Plate map, Protocol, Prep sheet |
| `Stepper` | Write · Plan · Run, on the live flow only |
| `SourceList` | what a rule rests on: one source per line, publisher first, the title as the link |
| `LinkCard` | a way on to another page: a title, one line of what is there, a chevron |
| `Notice` | a sentence in a box, in a tone: error, warning, note |

## The voice

The pages speak lab: "master mix", "tip rack", "slot 2", "20 µl", "well A1". Liquid names read as a
person writes them ("sample 1", not `sample_1`); wells as a person writes a range ("A1–A12, B1–B6
in slot 2"). About is in our own voice, first person. A finding says the step, the line, the wells
and the fix, in a sentence anyone in the lab can read.
