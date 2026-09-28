# Harness practices for the Nemotron loop

What people who run agent harnesses have measured, read against our loop (`provette/agent/`,
runs in `eval/agent/`), and what we took from it. Every claim has the page it was read on; the
last column says whether the loop does it.

## The practices

| # | practice | why (source) | in our loop |
|---|---|---|---|
| 1 | **Thinking budget, two calls** (Nano). Call 1 as now but `max_tokens = budget` (start at 12,000). If `finish_reason` is `length`, take `reasoning_content`, append `.\n</think>\n\n`, render the chat template ourselves with `continue_final_message=True`, and call `/v1/completions` with the rest of the turn's tokens; parse the `<tool_call>` text ourselves. | The tech report: the models "are trained to work with inference-time budget control... one can append the `</think>` token to the sequence and let the model continue to generate. The model will generate the response based on the partial thinking trace." ([arXiv 2512.20856, section 2.7](https://arxiv.org/html/2512.20856v1)). The client is on the model card and in the cookbook, and "will work with any OpenAI API compatible endpoint" ([Nano card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/raw/main/README.md), [vLLM cookbook cell 29](https://raw.githubusercontent.com/NVIDIA-NeMo/Nemotron/main/usage-cookbook/Nemotron-3-Nano/vllm_cookbook.ipynb)). | yes: a cut turn is continued with its reasoning closed (`provette/agent/loop.py`, `thinking_budget`) |
| 2 | **Send `reasoning_content` back** on our assistant messages inside the tool loop (both models). | The template keeps reasoning for assistant turns after the last user message and drops only older ones (`truncate_history_thinking`, [chat_template.jinja lines 13, 123–140](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/raw/main/chat_template.jinja)); "Reasoning ON: multi-step mode, where the model preserves and builds upon its prior chain-of-thought within a task" ([HF blog](https://huggingface.co/blog/nvidia/nemotron-3-nano-efficient-open-intelligent-models)). We send content only, so every past tool call of ours is rendered as `<think></think>` before it. | yes (`provette/agent/loop.py`) |
| 3 | **Collapse old check reports** in the messages we send: keep the latest `checks` in full, replace earlier ones with one line (draft N: simulator X, verify_exit, check_exit). The transcript on disk stays complete. | SWE-agent: "observations preceding the last 5 are each collapsed into a single line"; showing the full file "can easily flood a language agent's context window", 12.7% vs 18.0% ([arXiv 2405.15793](https://arxiv.org/html/2405.15793v3)). Anthropic: tools should "return only high signal information" ([writing tools](https://www.anthropic.com/engineering/writing-tools-for-agents)). | yes: `collapse_reasoning` and the check reports (`provette/agent/loop.py`) |
| 4 | **Super sampling to temperature 1.0, top_p 0.95.** | "Use `temperature=1.0` and `top_p=0.95` across **all tasks and serving backends** — reasoning, tool calling, and general chat alike" ([Super card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16/raw/main/README.md)). We run Super at Nano's 0.6/0.95. | yes (`provette/agent/llm.py`) |
| 5 | **Best-of-k with the checker as judge**: a flag in `eval/agent/run.py` that re-runs a missed request up to k times and keeps the first verified episode; report pass@1 and pass@k separately. | Coverage "scales with the number of samples over four orders of magnitude"; SWE-bench Lite "from 15.9% with one sample to 56% with 250 samples"; the gain is realised where answers "can be verified automatically" ([arXiv 2407.21787](https://arxiv.org/abs/2407.21787)). Our judge is deterministic. | yes: `--candidates` in `eval/agent/run.py`; the Nano rows are best of 3 |
| 6 | **Identical-draft detection**: hash each draft; if the same file comes back, say so, as we do for the same error. | OpenHands ships a stuck detector with defaults action-error 3, action-observation 4, monologue 3, alternating 6 ([stuck_detector.py](https://raw.githubusercontent.com/OpenHands/software-agent-sdk/main/openhands-sdk/openhands/sdk/conversation/stuck_detector.py), [types.py](https://raw.githubusercontent.com/OpenHands/software-agent-sdk/main/openhands-sdk/openhands/sdk/conversation/types.py)); its nudge reads like ours. Ours matches the same-error case only. | yes (`provette/agent/tools.py`) |
| 7 | **Quote the offending line** in a simulator rejection, not just its number. | SWE-agent's edit error shows "error type, attempted edit snippet, and original code"; Anthropic: "specific and actionable improvements, rather than opaque error codes or tracebacks" ([2405.15793](https://arxiv.org/html/2405.15793v3), [writing tools](https://www.anthropic.com/engineering/writing-tools-for-agents)). | yes: `offending_line` (`provette/agent/tools.py`) |
| 8 | **`presence_penalty` about 0.2–0.5 on Nano**, tested first on the transcript that degenerated. | Token Factory documents `presence_penalty` and `frequency_penalty` (−2 to 2) on both endpoints ([chat](https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion.md), [completions](https://docs.tokenfactory.nebius.com/api-reference/inference/create-completion.md)); `repetition_penalty` is not in its schema. NVIDIA filters training traces with "pathological repetition, such as repeated n-grams within a sliding window" but says nothing about inference penalties ([Nano card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/raw/main/README.md)). No source gives a value; the numbers here are ours. Prefer presence over frequency: a protocol repeats `transfer` on purpose. | not yet: the option is in `provette/agent/llm.py`, off by default |
| 9 | **Drop `run_checks`** (write_protocol already returns the checks). | "Important operations should be consolidated into as few actions as possible" ([2405.15793](https://arxiv.org/html/2405.15793v3)); "More tools don't always lead to better outcomes" ([writing tools](https://www.anthropic.com/engineering/writing-tools-for-agents)). | yes: `write_protocol` checks every draft, and `run_checks` is no longer offered (`provette/agent/tools.py`, `CALLABLE`) |
| 10 | **Repair turns with less thinking**: Super `low_effort: true`; Nano `enable_thinking: false` for the turn after a "stuck" message only. | Super: "Uses significantly fewer reasoning tokens than full thinking mode. Recommended as a starting point before tuning explicit token budgets"; the template appends `{reasoning effort: low}` to the last user message ([Super card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16/raw/main/README.md), [its template line 180](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16/raw/main/chat_template.jinja)). Nano's template has no `low_effort`. | not yet |
| 11 | **`force_nonempty_content: true`** (Super only), so a cut turn's text is returned and the fenced-block fallback can salvage a file. | The Super parser: "rare cases where the model will output only reasoning without an end-think token... End users may want to... always have a content response"; "For coding agents add" it ([super_v3_reasoning_parser.py](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16/raw/main/super_v3_reasoning_parser.py), [Super card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16/raw/main/README.md)). Nano's parser has no such switch. | not yet |

## Specific to Nemotron

**The thinking budget, and how to do it against Token Factory.** The chat
template is public and small (10.5 KB). Reasoning opens with the generation
prompt `<|im_start|>assistant\n<think>\n` and closes with `</think>`; a tool call
is rendered as `<tool_call>\n<function=NAME>\n<parameter=ARG>\nvalue\n</parameter>\n</function>\n</tool_call>`,
and a tool result as `<|im_start|>user\n<tool_response>\n...\n</tool_response>`
([chat_template.jinja](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/raw/main/chat_template.jinja)).
`<think>` is token 12 and `</think>` token 13
([tokenizer_config.json](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/raw/main/tokenizer_config.json)).
So `transformers.AutoTokenizer.from_pretrained(...).apply_chat_template(messages,
tools=SCHEMAS, tokenize=False, continue_final_message=True)` renders exactly what
the server renders; only the tokenizer files are needed, not the weights.

The two-call client in our loop: call 1 is today's chat call with `max_tokens` =
budget. If it stops on its own, nothing changes. If `finish_reason` is `length`,
`message.reasoning_content` (Token Factory's schema names both `reasoning_content`
and `reasoning`) is closed with `.\n</think>\n\n`, appended as an assistant
message, the template is rendered with `continue_final_message=True`, and
`/v1/completions` gets the string with `max_tokens` = the turn's remainder (the
file itself needs 4,000–6,000 of it). The completions endpoint returns text, so
the `<tool_call>` block is ours to parse. The model card's server-side variant
(the logit processor, which stops "at the next newline" within 500 tokens) needs a
`vllm serve` flag we do not control ([cookbook cells 32–43](https://raw.githubusercontent.com/NVIDIA-NeMo/Nemotron/main/usage-cookbook/Nemotron-3-Nano/vllm_cookbook.ipynb));
the client variant just cuts at the budget. The loop runs this way on Token Factory's
`/v1/completions` (row 1; `provette/agent/budget.py`).

**Sampling.** Nano: 1.0/1.0 for reasoning, 0.6/0.95 for tool calling, which we
use. Super: 1.0/0.95 for everything, which we use too. NVIDIA's own tool-calling
cell runs with an empty system prompt and `max_tokens` 512; the card recommends
"a high value (e.g., 10,000) for `max_tokens`" and its coding-agent config uses
32,000 ([Nano card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/raw/main/README.md), [Super card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16/raw/main/README.md)). Our 24,000 is in the band.
Token Factory's chat schema also lists `reasoning_effort` (none to max) with no
description; whether it reaches Nemotron's `low_effort` is untested.

**Toggles per turn.** `enable_thinking` and `low_effort` are `chat_template_kwargs`,
set per request, so a repair turn can differ from a writing turn (row 10). The
card's `/think` in the system prompt is only an example string.

**Whole file, not edits.** The template renders a tool argument as raw text
between `<parameter>` tags, so the model writes the file without JSON escaping;
Anthropic's warning about "string-escaping any code it writes"
([building effective agents](https://www.anthropic.com/engineering/building-effective-agents))
does not bite here. SWE-agent found 51.7% of trajectories contain a failed edit
and success "drops to 57.2% after one failed edit" ([2405.15793](https://arxiv.org/html/2405.15793v3)):
edits add a failure mode we do not have. Keep the whole file.

## General, and what we already do

* **Check on every write** — done (`write_protocol` runs the checks; prelint).
  SWE-agent's linting guardrail: 18.0% with, 15.0% without.
* **Hints on errors** — done for eight error kinds; row 7 adds the source line.
* **Stuck after three identical errors** — done, and it matches OpenHands'
  default of 3; our idle-turn stop matches its monologue threshold of 3. Row 6
  adds the identical-action case. ReAct already saw the model "repetitively
  generates the previous thoughts and actions" as its main reasoning error
  ([arXiv 2210.03629](https://arxiv.org/html/2210.03629)).
* **A cap, then submit what exists** — done (the harness checks the final
  draft); SWE-agent: "if a run exceeded this budget, existing edits were
  submitted automatically". Its successful runs took a median of 12 steps,
  failed ones a mean of 21; our 25 calls sit there.
* **Tool descriptions written for a new hire** — done; "even small refinements
  to tool descriptions can yield dramatic improvements" ([writing tools](https://www.anthropic.com/engineering/writing-tools-for-agents)).
* **Ground truth from the environment each step** — done; it is the frame.
* **NeMo Agent Toolkit** gives no Nemotron-specific harness guidance: its
  reasoning agent plans once up front with a `<think>` model and "does not
  revisit the plan" ([docs](https://docs.nvidia.com/nemo/agent-toolkit/1.3/workflows/about/reasoning-agent.html)); the cookbook's agentic page is
  configs for OpenCode and OpenHands with Super at 1.0/0.95 and 32,000 output
  tokens ([OpenScaffoldingResources](https://raw.githubusercontent.com/NVIDIA-NeMo/Nemotron/main/usage-cookbook/Nemotron-3-Super/OpenScaffoldingResources/README.md)).

## What we could not find

* Any NVIDIA number for how the thinking budget changes accuracy on tool use:
  the tech report's Figure 8 is a curve for Nano with no benchmark named in the
  text we could read; the report says nothing about sampling, max output length,
  or repetition at inference.
* Any recommended `presence_penalty` or `repetition_penalty` for Nemotron 3,
  from NVIDIA, vLLM or Nebius; and whether Token Factory forwards
  `repetition_penalty` through `extra_body`.
* Any measured result for reasoning-off or low-effort on repair turns only.
* The vLLM blog's text on the budget beyond one line ("prevents the model from
  overthinking", [post source](https://raw.githubusercontent.com/vllm-project/vllm-project.github.io/main/_posts/2025-12-15-run-nvidia-nemotron-3-nano.md)); it serves Nano with `--reasoning-parser deepseek_r1`, the card with `nano_v3`.
* A CodeAct or OpenHands ablation that isolates action-space size; the CodeAct
  abstract claims "up to 20% higher success rate" for code actions over JSON
  ([arXiv 2402.01030](https://arxiv.org/abs/2402.01030)), which is a different
  design from ours and not evidence about our seven tools.
