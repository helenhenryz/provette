# eval/ledger/ — the ledger over the public Opentrons protocol library

Every check Provette makes reads one record: the ledger of what the run did, every action with
its well, its volume and its line (`provette/trace`), and what that left in every well and on
every tip (`provette/state`). If the record is wrong, every check is wrong with it. So the
ledger, read from the simulator's own command broker, is checked against `opentrons.cli
analyze`, Opentrons' official analysis of the same protocol, and the two must agree (D-09).
From API level 2.14 the analysis is independent of the messages the ledger reads; below it,
Opentrons builds the analysis from the same messages, so there the check tests our reading of
them, not the messages (D-10).

This measures that on protocols written for the OT-2 by people who are not us: every protocol
of Opentrons/Protocols at the pinned commit (D-05). Nothing from the library is stored here:
the library is fetched into `.cache/`, and this folder holds counts.

```
env -u PYTHONPATH uv run provette corpus run --worker provette.corpus.workers:trace_worker --jobs 10
env -u PYTHONPATH uv run provette corpus run --worker provette.corpus.workers:export_worker --jobs 10
env -u PYTHONPATH uv run python eval/ledger/build.py
```

`build.py` writes `counts.json`. What the replay draws on the same protocols, and why the ones
the simulator refuses are refused, is in [`docs/replay-support.md`](../../docs/replay-support.md).

## Results

Of **833** library protocols, the simulator and the tracer accept **788**. On **788 of 788**
Opentrons' analysis agrees with the ledger, over 974,124 recorded events; **16 of 16** of them
are written for API 2.14 or later, where the analysis is a fully independent reading. The
replay exports **787 of 788**.

| step | protocols |
|---|---|
| in the library | 833 |
| the simulator and the tracer accept | 788 |
| Opentrons' analysis agrees with the ledger | 788 of 788 |
| of those, a fully independent reading (API 2.14 and later) | 16 of 16 |
| the replay exports | 787 of 788 |
