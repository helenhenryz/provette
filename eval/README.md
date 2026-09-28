# eval/ — the evaluation

What Provette's numbers rest on. Every number on the Methods and About pages is computed from a
file under the `results/` folders here when the page loads (`api/evidence.py`), and
`tests/api/test_evidence.py` holds each README to the same files, so a page, a README and a
result cannot disagree.

| folder | the question | model calls |
|---|---|---|
| [`checks/`](checks/README.md) | Do correct protocols verify, and only against their own maps? Do the checks catch bugs the simulator passes? Does the prep sheet match one worked out by hand? | none |
| [`agent/`](agent/README.md) | With the checks as its tools, how often does Nemotron write a protocol that verifies, and at what cost? | Super and Nano |
| [`baseline/`](baseline/README.md) | The same model with the twelve rules written into its prompt and no checker | Super |
| [`planner/`](planner/README.md) | Can the model propose the plate map from the request, and does the map hold up? | Super |
| [`audit/`](audit/README.md) | What do the rules find in the public Opentrons protocol library? | none |
| [`ledger/`](ledger/README.md) | Does the record every check reads hold up on the public library: does Opentrons' own analysis of each run agree with it? | none |

The inputs, fixed before any protocol was run:

| folder | what |
|---|---|
| [`requests/`](requests/README.md) | 30 requests written the way a scientist asks, and the reference sheet every model gets |
| [`requests-hard/`](requests-hard/README.md) | 15 harder requests, each with its own plate map |
| [`platemaps/`](platemaps/build.py) | the plate maps of the 17 requests that have one, written from the request text alone |
| [`checks/protocols/`](checks/protocols/) | 34 correct protocols for those 17 requests, in two wordings, written by us in a session that never saw Provette |
| [`prices.json`](prices.json) | Token Factory's list prices, for every dollar on the pages |

The agent and planner runs use the product's settings (`api/run_settings.py`, D-32, D-33):
25 tool calls and 100,000 tokens a run, at least three drafts before a rejected one is taken,
12 tool calls and 40,000 tokens a plan, and the planner may say a message is not a request.
Everything runs from the repository root; the model runs need
`set -a; . ~/.config/provette/token-factory.env; set +a` first.
