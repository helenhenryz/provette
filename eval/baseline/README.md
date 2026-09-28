# eval/baseline/ — the rules in the prompt, no checker

Is it the loop that matters, or would telling the model the rules do? The same 34 requests as
`eval/agent/results/super` (17 with a plate map, both wordings), the same model, but no tools
and no checker: the twelve rules the checks grade by are written into the system prompt in
words (`--rules-in-prompt`, the text is `rules_section()` in `run.py`), and the model writes one
draft (`--one-shot-only`). The draft is graded by `provette verify` and `provette check` exactly
as the agent's are, and "verified and clean" means the same.

```
env -u PYTHONPATH uv run python eval/baseline/run.py --model nvidia/nemotron-3-super-120b-a12b \
    --rules-in-prompt --one-shot-only --out eval/baseline/results/super-rules-in-prompt
env -u PYTHONPATH uv run python eval/agent/tabulate.py eval/baseline/results/super-rules-in-prompt
```

The result is quoted beside the agent's (D-30): as evidence for the loop, never as a page about
the model's mistakes.

## Results

Super, the twelve rules in its prompt, one draft each (`results/super-rules-in-prompt`, $0.37):

| | of 34 |
|---|---|
| rejected by the simulator | 5 |
| passed the simulator | 29 |
| of those, broke a rule it had just been told (an error or a warning) | 19 |
| of those, a plate map mismatch | 14 |
| **verified and clean** | **7** |

The rules it broke, in drafts: `CONTAM-STOCK` 9, `SOURCE-TOO-SHALLOW` 7, `PIPETTE-RANGE` 6,
`UNMIXED-AT-END` 2, `MIX-TOO-WEAK` 2, `WELL-CAPACITY` 1, `MIX-BEFORE-DRAW` 1. With the checks in
its loop instead, the same model on the same requests verifies 31 of 34
(`eval/agent/README.md`): what moves the number is a report it can act on, not knowing the rule.
