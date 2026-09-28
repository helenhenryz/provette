# eval/audit/ — the rules over the public Opentrons protocol library

The eleven rules that run without a plate map (`provette/rules/README.md`; the twelfth,
`LABWARE-FOR-TECHNIQUE`, needs the map) over every protocol of Opentrons/Protocols at the pinned
commit (D-05), each with its parameters at the library's defaults (`fields.json`). Nothing from
the library is stored here: the library is fetched into `.cache/`, and this folder holds counts,
slugs, line numbers and links.

```
env -u PYTHONPATH uv run provette corpus run --worker provette.corpus.workers:check_worker
env -u PYTHONPATH uv run python eval/audit/build.py
```

`build.py` writes `counts.json` (findings by rule and severity, protocols by worst finding, by
category) and `triage.csv`: one row per finding a person should judge (every error, every
uncertain warning, and a sample of the rest), with a link to the protocol and two empty columns,
the verdict (real, deliberate, false alarm, not sure) and why. We fill those in; the labels are
each rule's precision, and until they exist a count is a count of findings, not of problems.

## Why no headline number comes from here yet

1. **Parameters take the library's default values.** A protocol whose default sample volume is
   10 µl may never be run that way.
2. **Almost no library protocol declares its liquids** (11 of 833), so the structural rules
   cannot tell eight replicates from eight samples, and a contamination error on an undeclared
   plate is a finding to judge, not a verdict (D-17, D-19).
3. **No one outside the team has judged a finding yet.**

The reads that set each rule's thresholds on this library, twenty protocols a rule, are under
the rule's specification in `docs/detection-catalogue.md`.

## Results

787 of 833 library protocols check (46 do not simulate on 8.8.2);
findings, not problems, as the section above says.

| protocols by worst finding | count |
|---|---|
| an error | 218 |
| a warning at most | 223 |
| a note at most | 67 |
| nothing | 279 |

| rule | error | warning | note |
|---|---|---|---|
| `CONTAM-STOCK` | 171 | 196 | 162 |
| `PIPETTE-RANGE` | 407 |  |  |
| `MIX-BEFORE-DRAW` |  | 297 |  |
| `MIX-TOO-WEAK` |  | 184 |  |
| `UNMIXED-AT-END` |  |  | 130 |
| `WELL-CAPACITY` | 36 | 82 | 1 |
| `CONTAM-WELL` |  | 39 | 15 |
| `COLD-MODULE-NEVER-SET` |  | 48 |  |
| `SOURCE-TOO-SHALLOW` | 2 |  |  |
| `NO-SAMPLE-INTO-REAGENT-WELL` |  |  | 1 |

`ENZYME-BEFORE-DILUENT` and `NO-NEGATIVE-CONTROL` need declared liquids and are silent here.
`triage.csv` holds 942 rows for a person to judge: every error, every uncertain finding, and a
sample of the rest.
