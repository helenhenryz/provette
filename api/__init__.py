"""The Provette web API: the product's backend.

It wraps `provette` and never reimplements it: `provette.check.check`,
`provette.intent.cli.verify`, `provette.view` for the replay, `provette.planner` for the plate
map and `provette.agent.loop` for the live episode. The pages under `web/` render what these
return. See `api/README.md`.
"""
