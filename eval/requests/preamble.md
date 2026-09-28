Write a complete Opentrons OT-2 protocol in Python (Protocol API version 2, apiLevel 2.19) for the request below.

Requirements:
- One Python file with `metadata` or `requirements`, and a `run(protocol)` function.
- Use standard Opentrons labware and OT-2 GEN2 pipettes only. No custom labware.
- Declare every liquid that is on the deck at the start with `protocol.define_liquid(...)` and `well.load_liquid(...)`, one liquid definition per distinct liquid (each sample is its own liquid), with realistic starting volumes.
- The protocol must pass `opentrons_simulate` with no error.
- Output only the Python file.

Request:
