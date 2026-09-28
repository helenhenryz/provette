# provette/corpus

The public Opentrons protocol library, used as a test corpus: 833 protocols that
other people wrote and that pass the simulator. This module fetches the library
at one pinned commit, gives each protocol the parameters it needs to run, runs a
command over all of them in parallel, and counts what happened. It knows nothing
about traces, state or rules; those plug in as a *worker*.

## The legal position

The library has no license, so by default every right in it is reserved
([`DECISIONS.md`](../../DECISIONS.md) D-05). It is fetched at run time into
`.cache/`, which is gitignored, and nothing from it is ever committed here: we
publish slugs, line numbers, findings and short quoted snippets. The test
fixtures in `tests/corpus/` imitate the layout of a library folder and were
written from scratch.

## What may be relied on

| call | what it promises |
|---|---|
| `fetch(cache_dir=.cache/opentrons-protocols)` | The checkout is at exactly `LIBRARY_COMMIT` when it returns, or it raises. A second call does not touch the network. Only `protocols/` and `protolib/` are checked out |
| `discover(checkout)` | One `LibraryProtocol` per folder, sorted by slug: the `.py`, `fields.json`, the custom labware folder, the apiLevel, the README categories (normalised, and raw), and the `.hide-from-search` and `.ignore` markers. 833 at the pinned commit |
| `prepare(protocol, out_dir, overrides=None)` | A runnable copy with `get_values()` prepended, built the way the library's own build tool does it (`protolib/parse/parseOT2v2.py`): the first option of a dropDown, otherwise `default`. `overrides` replaces individual values; an unknown name is an error |
| `PreparedProtocol.original_line(n)` | Line `n` of the prepared file as a line of the original source, or `None` inside the prepended function. `line_offset` is 5 with a `fields.json` and 0 without |
| `tip_reuse_parameters(protocol)` | The parameters that let the user reuse, park or change tips, with type, default and options. Parameters that track tips *between runs* (`tip_track`) are left out. 65 protocols have at least one |
| `run_corpus(prepared, worker, jobs=, timeout_s=, out_path=, force=False)` | One JSON line per protocol, written as each finishes. Each protocol runs in a process of its own, killed with everything it started at the timeout. A re-run skips slugs already in the file |
| `summarise(out_path)`, `render(summary)` | Counts by status, by failure reason, by category and by apiLevel, as data and as text |

One line of a results file:

```json
{"slug": "...", "status": "ok|error|timeout", "seconds": 1.4,
 "error_class": null, "error_message": null, "error_line": null,
 "api_level": "2.13", "categories": ["PCR"], "payload": {"commands": 132}}
```

`error_message` is the first line of the message. `error_line` is the line in
the **original** source when the simulator names one.

### Writing a worker

A worker is any function `worker(prepared: dict) -> dict`, named on the command
line as `package.module:function`. It receives `PreparedProtocol.to_dict()`
(`slug`, `path`, `original_path`, `labware_dir`, `line_offset`, `values`,
`api_level`, `categories`) and returns a JSON-serialisable dict, which becomes
`payload`. If it raises, the protocol is recorded as an error with the class and
the first line of the message. It runs alone in a fresh process, so it may patch
the simulator freely. `workers.simulate_worker` is the model to copy;
`workers.trace_worker` traces from both sources, replays, and counts what the contact model
could not decide (validation layer 2 over the library), and `workers.check_worker` runs the
rules (`eval/audit/`).

## How to run it

```
env -u PYTHONPATH uv run provette corpus fetch
env -u PYTHONPATH uv run provette corpus list --category "PCR"
env -u PYTHONPATH uv run provette corpus run --jobs 12          # simulate_worker, whole library
env -u PYTHONPATH uv run provette corpus run --worker pkg.mod:fn --slug 00222e --force
env -u PYTHONPATH uv run provette corpus summary [file]
```

Results go to `.cache/corpus/<worker function>.jsonl`, prepared copies to
`.cache/corpus/prepared/<slug>/`. The network tests run with `PROVETTE_NETWORK=1`.

## Measured

Whole library, `simulate_worker`, 12 jobs, `opentrons==8.8.2`, a 24-core machine. Fetch: 7.5 s, 66 MB on disk.

| | Python 3.10.21 (what the project is pinned to) | Python 3.12.14 |
|---|---|---|
| ok | **790 of 833** (94.8%) | **417 of 833** (50.1%) |
| error | 43 | 416 |
| timeout | 0 | 0 |
| wall clock | 217 s | 118 s |

The 3.10 figure is the survey's, exactly. The 43 that fail there:

| count | why |
|---|---|
| 30 | private or removed API internals (`_implementation`, `_impl`, `protocol_api.contexts`, `update_config_item`) — D-06 |
| 4 | `PipetteTipType` KeyError |
| 3 | apiLevel too low for a call the protocol makes |
| 2 | custom labware missing from the folder |
| 2 | labware too tall |
| 2 | other |

**Why 3.12 loses 373 more.** For protocols below apiLevel 2.14, `opentrons`
8.8.2 finds a hardware module's definition file by formatting an enum into a
file name. Python 3.11 changed what formatting such an enum gives: measured,
`f"{MagneticModuleModel.MAGNETIC_V2}"` is `magneticModuleV2` on 3.10 and
`MagneticModuleModel.MAGNETIC_V2` on 3.11 and 3.12. So every older protocol that
loads a magnetic, temperature, thermocycler or heater-shaker module fails with
`NoSuchModuleError`: 393 protocols. The summary gives them their own row,
"module lookup broken by Python 3.11+", because it is not a fault of the
protocol. The project is pinned to Python 3.10 for this reason (DECISIONS.md D-04).

Library-prep and extraction protocols, the ones the bead-cleanup rules are for,
are hit hardest: NGS Library Prep is 199 of 201 on 3.10 and 31 of 201 on 3.12.

## Known gaps

* A protocol is untrusted code. Its process gets a hard timeout and its own
  process group, but no sandbox: it can read and write files as the user.
* `textFile` parameters get the library's default CSV. Protocols whose default
  is an empty string run with no input and may do nothing.
* Tip-reuse parameters are found by name and label. The pattern was tuned on
  this commit of the library (it finds the survey's 65), not validated elsewhere.
* Category normalisation settles the spelling variants seen at this commit; a
  new variant passes through with only its lowercase words capitalised.
* Every library folder has exactly one `.py`. If one ever had two, `discover`
  takes the first by name.
