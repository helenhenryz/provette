# eval/requests-hard/

Fifteen requests written to be harder than [`eval/requests/`](../requests/README.md)
in the way a lab is hard: volumes that force a plate or tube choice, reagents that must
stay cold and go in last, dilution series that must be mixed, a trough that runs shallow
before it runs dry, plates that need their controls, and techniques whose labware is easy
to get wrong. Same form as the original set: `requests.jsonl` has `id`, `technique` and
`request`; the requests say nothing about tips, contamination, mixing or controls unless
the scientist would; `build.py` writes one plate map per request from the request text
alone, with the arithmetic from `provette.calc`, in the format of `provette/intent/spec.py`.
Every map loads, and four of the trickiest (`hard-dil-02`, `hard-cherry-01`, `hard-mic-01`,
`hard-elisa-01`) were verified against a known-correct protocol. Nothing here is
copied from the Opentrons library (D-05).

| id | what makes it hard | what a naive draft is expected to trip |
|---|---|---|
| `hard-dil-01` | 500 µl dilutions (50 serum + 450 PBS) need a deep-well plate; the ELISA plate must be flat; 1:10 must be mixed before the duplicates are drawn | `WELL-CAPACITY` (500 µl in a flat or PCR plate), `MIX-BEFORE-DRAW`, `LABWARE-FOR-TECHNIQUE` |
| `hard-pool-01` | 96 × 25 µl is 2.4 ml: not a 1.5 ml or 2 ml tube; 96 indexed libraries through one tip when tips are short | `WELL-CAPACITY` (over the rim of a 1.5 ml tube), `CONTAM-STOCK` under short-on-tips, `PIPETTE-RANGE` if a P300 draws 25 µl |
| `hard-qpcr-01` | three primer pairs, 81 wells, and the NTC wells are in the map, so a plate without them does not verify; master mix, primers and cDNA on a cold block | plate map (missing NTCs), `COLD-MODULE-NEVER-SET`, `ENZYME-BEFORE-DILUENT` (mix before water), `LABWARE-FOR-TECHNIQUE` (flat plate), `UNMIXED-AT-END` |
| `hard-dil-02` | a 1:3 series in DMSO, then 10 µl of every point into wells that already hold medium (the map uses `declared`); points 5 and 6 carry under 0.2 µl of compound, so any unmixed step shows | `MIX-BEFORE-DRAW`, `MIX-TOO-WEAK`, `PIPETTE-RANGE` (10 µl on a P300), `VOLATILE-OR-VISCOUS` when it exists |
| `hard-norm-01` | 48 libraries at 5.5 to 80 nM to 4 nM in 20 µl: volumes from 1.0 to 14.5 µl, every one different; the normalised wells are never drawn from, so only the end-of-run mix rule sees an unmixed plate | `UNMIXED-AT-END`, `PIPETTE-RANGE` (a P300 for 1 µl), plate map (arithmetic) |
| `hard-clone-01` | ligase and buffer at 4 °C on a cold block; the enzyme must go in last; 1 µl of ligase | `COLD-MODULE-NEVER-SET`, `ENZYME-BEFORE-DILUENT`, `PIPETTE-RANGE`, `NO-MASTER-MIX` when it exists |
| `hard-pcr-01` | 96 × 15 µl from 1.6 ml: enough by count, but 160 µl left in a 12-channel reservoir is 0.8 mm deep and 2 ml in the 195 ml trough falls under the tip halfway; a tube on the block is the answer | `SOURCE-TOO-SHALLOW`, prep sheet "no margin", `CONTAM-STOCK` if one tip does the templates |
| `hard-elisa-01` | a 7-point 1:2 standard series made on the deck at 250 µl per point (500 µl in a point before it is passed on: not a flat plate), two readings of "point 1", a blank, then duplicates of 32 sera on a coated plate | `WELL-CAPACITY`, `MIX-BEFORE-DRAW`, `LABWARE-FOR-TECHNIQUE` (PCR plate as ELISA plate), `MIX-TOO-WEAK` |
| `hard-cell-01` | three suspensions from 15 ml tubes, 32 wells each, pinned by column block; cells settle during a 96-well series and one tip across lines carries cells between them | `CONTAM-STOCK` (one tip for all three tubes), `SUSPENSION-SETTLED` when it exists |
| `hard-bca-01` | 96 wells at 225 µl (25 + 200): over the working volume of a 200 µl flat plate and over the rim of a PCR plate; a standard series made on the deck plus a blank; 40 samples in duplicate | `WELL-CAPACITY`, `MIX-BEFORE-DRAW`, `UNMIXED-AT-END`, `LABWARE-FOR-TECHNIQUE` |
| `hard-pcr-02` | 100 µl reactions: a plate rated 100 µl is at its working volume and any mix spills it; the 200 µl PCR plate or strips are the answer | `WELL-CAPACITY` (brim while mixing), `ENZYME-BEFORE-DILUENT` |
| `hard-pcr-03` | seven components, 0.25 µl of polymerase and 0.5 µl of dNTPs per reaction: only a master mix can do it; components on a cold block; 48 templates | `PIPETTE-RANGE`, `COLD-MODULE-NEVER-SET`, `ENZYME-BEFORE-DILUENT`, `NO-MASTER-MIX` when it exists, `CONTAM-STOCK` (one tip through 48 templates) |
| `hard-cherry-01` | a 384-well source (well names to P24), 2 µl picks on a P20, two readings of "consecutive", then master mix on top of 2 µl | `PIPETTE-RANGE`, plate map (order), `UNMIXED-AT-END`, `CONTAM-WELL` if the mix tip enters the picked wells |
| `hard-mic-01` | two antibiotics in two pinned rows, 1:2 across ten columns starting at 1:2, then culture into columns 1 to 11 and a broth-only column 12; two readings of the last column; the culture tip must not go back into the broth | `MIX-BEFORE-DRAW`, `CONTAM-STOCK` (culture into the broth reservoir), `MIX-TOO-WEAK`, plate map (controls) |
| `hard-rt-01` | twelve RT reactions and twelve no-RT controls in the map, 1 µl of enzyme last, everything on a cold block, RNA in a plate | plate map (missing no-RT wells), `COLD-MODULE-NEVER-SET`, `ENZYME-BEFORE-DILUENT`, `PIPETTE-RANGE` |

Two rows use a technique word the original set does not (`Protein assay` for the BCA;
`Cell culture` for the seeding, which exists); `LABWARE-FOR-TECHNIQUE`'s table should
map `Protein assay` to a flat plate. Every request is doable on an OT-2 with GEN2
pipettes and standard labware; where the plate map admits two readings of the request
(which row, point 1 neat or 1:2, the last well's excess) both are variants, as in the
original set.

```
env -u PYTHONPATH uv run python eval/requests-hard/build.py    # rewrite the maps
```
