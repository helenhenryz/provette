# Changelog

## 1.0.0

The first release, entered in the Nebius x NVIDIA Global AI Hackathon.

**The checker.** A protocol runs in the Opentrons simulator (8.8.2); every action is recorded
from two readings that must agree; a replay follows every microlitre through every tip and well;
twelve checks read it (carry-over, mixing, pipette range, well capacity, a shallow source, a
cold module never set, controls, an enzyme before its diluent, the labware a technique needs) and a plate map says what every
well must hold. Every finding names the line, the wells and the fix. `provette check`,
`provette verify` and `provette view` on the command line.

**The agent.** NVIDIA Nemotron on Nebius Token Factory plans the plate map, then writes the
protocol with the checks as its tools and repairs what they reject; the model is never the
judge. A draft the checks reject is sent back until the third (D-32), and a message that is not
a lab request is said to be one rather than planned (D-33).

**The product.** Write a request and watch it planned, written, checked and repaired; check a
protocol you already have, with no model; replay any run in 2D and 3D; read the rules, the
words they use and what they do not cover; teach a word or propose a rule from the pages; pin
or delete anything in the history; change the run and plan budgets in Settings, and reset them.
The numbers behind it are on Methods and About, computed from `eval/`.

**The evidence.** [`eval/`](eval/README.md): the checks on correct protocols and on planted bugs,
Super and Nano writing with the checks as tools, the same rules written into the prompt without
the checker, and the planner. What is not done is in [`docs/roadmap.md`](docs/roadmap.md).
