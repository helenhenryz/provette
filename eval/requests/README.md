# eval/requests/

The fixed set of plain-English requests the agent evaluation runs on
([`docs/how-it-works.md`](../../docs/how-it-works.md), "The evidence").

**The requests are written the way a scientist would ask, and they say nothing
about tips, contamination, mixing or controls.** Whether the writer thinks of
those unprompted is the thing being measured. Do not "improve" a request by
adding a hint; add a new request instead, and never remove one, because every
published number is over this set.

`requests.jsonl` has one request per line: `id`, `technique`, `request`.

Every writer gets the same preamble, in `preamble.md`. It asks for a complete
OT-2 protocol that declares its starting liquids, which Provette needs in order to
know what is a sample and what is a reagent. It asks for nothing else.
