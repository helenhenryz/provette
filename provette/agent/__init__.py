"""The agent: a Nemotron model that writes a protocol, checks it with tools, and repairs it.

The model never judges a protocol. It hands a draft in with `write_protocol`, which runs the
simulator, `provette verify` and `provette check` somewhere the model cannot tamper with (see
`provette.agent.runner`), and reads what comes back.
"""
