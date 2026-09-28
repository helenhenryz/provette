"""The planner: a model proposes the plate map a request asks for, and a person approves it.

The first stage of the pipeline (`docs/how-it-works.md`). The model reads the request and hands
in a plate map in the format of `provette.intent.spec`; it never computes a number (the
calculators of `provette.calc` are its tools, and `propose_platemap` refuses a volume it was not
given), and a budget that runs out is an error, never a guessed map.
"""

from provette.planner.loop import DEFAULT_MODEL, PlanError, Planning, plan, plan_platemap

__all__ = ["DEFAULT_MODEL", "PlanError", "Planning", "plan", "plan_platemap"]
