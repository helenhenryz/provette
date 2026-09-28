/* The one typed contract with the backend (docs/ui-brief.md, "Engineering").

   The API returns the pipeline's own JSON. The types here name the fields the pages rely on
   and leave the rest open (`[key: string]: unknown`), so a new field from `provette` arrives
   without a change here, and the generic renderers (findings, steps, prep rows) show it. */

export type Severity = "error" | "warning" | "note";

export interface Finding {
  source?: "check" | "verify"; // set by the page: where the finding came from
  rule_id: string;
  severity: Severity;
  certain: boolean;
  line: number | null;
  title: string;
  explanation: string;
  fix: string;
  [key: string]: unknown;
}

export interface Outcome {
  verified: boolean;
  sentence: string;
  stop_reason: string;
  submitted: boolean;
  final_draft: number | null;
  findings: Finding[];
}

export interface EpisodeCard {
  id: string;
  set: string;
  run_label: string; // "one try" or "best of 3"
  condition: string;
  condition_label: string;
  request_id: string;
  technique: string | null;
  request: string;
  model: string;
  model_label: string;
  runner: string | null;
  runner_label: string;
  candidates: {
    n: number;
    verified: number;
    chosen: string | null;
    rows: {
      dir: string;
      verified: boolean;
      stop_reason: string | null;
      tokens_in: number;
      tokens_out: number;
    }[];
  } | null;
  verified: boolean;
  outcome: Outcome;
  drafts: number | null;
  tool_calls: number | null;
  tokens_in: number | null;
  tokens_out: number | null;
  cost_usd: number | null;
  seconds: number | null;
  stop_reason: string | null;
}

export type StepStatus = "ok" | "rejected" | "problem" | "info";

export interface Step {
  turn: number;
  kind: "tool" | "text" | "error";
  tool: string | null;
  title: string;
  detail: string;
  status: StepStatus;
  draft: number | null;
  seconds: number | null;
  tokens_out: number | null;
  reasoning_chars: number;
  reasoning?: string; // the model's own thinking before the call, clipped
  arguments?: string; // what the model sent the tool, as JSON, clipped
  report?: string; // a run_checks step: the verdict text the model received, whole
  cut: boolean;
  continued?: boolean; // the reasoning went past its budget and the turn still produced its call
}

export interface DraftRow {
  n: number;
  lines: number;
  checked: boolean;
  repaired?: boolean; // prelint repaired known slips before checking; as_written is kept
  summary: { title: string; detail: string; status: StepStatus } | null;
  simulator?: "passed" | "rejected" | "timeout"; // timeout: the checks did not finish, no verdict
  verify_exit?: number | null;
  check_exit?: number | null;
  findings?: Finding[];
  wells_ok?: number | null;
  wells_total?: number | null;
  simulator_error?: string | null;
  report?: string; // the verify and check reports of this draft, as written
}

/* The plate map, as provette/intent/spec.py writes it. */
export type Amount = number | "declared";
export type Contents = Record<string, Amount>;

export interface PlateMapGroup {
  name: string;
  members: Contents[];
  within: string[] | null;
  position: "free" | "same_as_source";
  order_hint: "index" | null;
}

export interface PlateMapVariant {
  name: string;
  why: string;
  pinned: Record<string, Contents>;
  groups: PlateMapGroup[];
  widened?: string;
}

export interface PlateMap {
  id: string;
  request: string;
  liquids: {
    name: string;
    role: "sample" | "reagent";
    bind: string;
    pattern: string;
    count?: number;
  }[];
  destination: { select: string; pattern?: string };
  technique?: string | null;
  variants: PlateMapVariant[];
  discard_intended: string[];
  notes: string[];
}

export interface EpisodeDetail extends EpisodeCard {
  done: Record<string, unknown>;
  platemap: PlateMap | null;
  steps: Step[];
  draft_rows: DraftRow[];
  final_draft: number | null;
  prices_read_on: string | null;
}

export interface Draft {
  n: number;
  text: string;
  as_written?: string | null; // the model's own text, before prelint's repairs
  checks: Record<string, unknown> | null;
}

/* The prep sheet (provette/intent/prep.py, as provette.intent.report.prep_json writes it): what to
   load in every source well and whether it would run dry. Under `verify.prep` when a plate map
   was given, and under the analysis's own `prep` for every protocol the simulator passes. */
export interface PrepJson {
  lines: {
    slot: string;
    labware: string;
    well: string;
    liquid: string;
    declared_ul: number | null;
    needed_ul: number;
    flag: "would_run_dry" | "no_margin" | "draws_air" | null;
    already_in_plate?: boolean; // declared and never drawn down: say so, not "load 0"
  }[];
  tips: { slot: string; rack: string; tips: number }[];
}

/* `provette verify --json` */
export interface VerifyIssue {
  kind: string;
  liquid: string | null; // null on an `unexpected_well`: the map names no liquid for that well
  expected_ul: number | null;
  found_ul: number | null;
  detail: string;
}

export interface VerifyMismatch {
  well: string | null;
  group: string | null;
  expected: Record<string, number>;
  found: Record<string, number>;
  issues: VerifyIssue[];
  text?: string[];
  well_index?: number | null;
}

export interface VerifyWell extends VerifyMismatch {
  ok: boolean;
}

export interface VerifyReport {
  protocol: string;
  platemap: string;
  exit_code: number;
  intent: {
    status: "verified" | "mismatch" | "cannot_check";
    destination: string | null;
    variant: string | null;
    problems: string[];
    notes: string[];
    wells_ok: number;
    wells_total: number;
    mismatches: VerifyMismatch[];
    wells?: VerifyWell[]; // every checked well, once provette lists them (docs/ui-needs.md #1)
  };
  accounting: {
    liquid: string;
    logical: string | null;
    role: string;
    declared_ul: number;
    delivered_ul: number;
    left_in_source_ul: number;
    elsewhere: { well: string; ul: number }[];
    trash_ul: number;
    lost_ul: number;
    flags: string[];
    notes: string[];
  }[];
  prep: PrepJson;
  technique?: string | null;
  labware?: Finding[]; // LABWARE-FOR-TECHNIQUE: findings that run in verify (provette/intent/labware.py)
  unplaced_liquids?: UnplacedLiquid[];
  destination_name?: string | null;
  flags?: string[];
  text?: string;
}

/* `provette check --json` */
export interface CheckReport {
  schema_version: number;
  protocol: string;
  api_level: string;
  simulator: { passed: boolean; opentrons_version: string };
  rules: RuleRow[];
  counts: {
    by_severity: Record<string, number>;
    by_rule: Record<string, number>;
  };
  findings: Finding[];
  unplaced_liquids?: UnplacedLiquid[];
}

export interface RuleRow {
  rule_id: string;
  family: number;
  tier: string;
  title?: string;
  description: string;
  status?: "proposed" | "adopted";
  proposed_by?: string;
  sources?: { name: string; url: string }[];
}

/* `provette view`'s export (provette/view/README.md, "How the deltas work") */
export type Band = [
  origin: number,
  volume: number | null,
  mode: 0 | 1,
  certain: 0 | 1,
];
export type WellRow = [
  volume: number | null,
  max: number | null,
  bands: Band[],
];

export interface ReplayWellGeometry {
  x: number;
  y: number;
  shape: string;
  d: number | null;
  w: number | null;
  h: number | null;
  depth: number | null;
  max: number | null;
  /* schema 2: the definition's word for the well's bottom, and the ledger's own table of
     [µl, mm] rows from [0, 0] to the brim (provette.model.WellGeometry.height_at_ul); absent or
     null when the definition gives no shape, and absent in a schema 1 export */
  bottom?: "flat" | "u" | "v" | null;
  height_at_ul?: [number, number][] | null;
}

/* provette/view/export.py, `_labware_row` */
export interface ReplayLabware {
  id: string; // "4:nest_96_wellplate_200ul_flat"
  slot: string;
  name: string; // the label the author gave, or the display name
  load_name: string;
  is_tiprack: boolean;
  is_trash: boolean;
  module: string | null;
  kind: string;
  measured: boolean; // false: well positions are a guess
  slot_x: number;
  slot_y: number;
  w: number;
  h: number;
  ox: number;
  oy: number;
  wells: Record<string, ReplayWellGeometry>;
}

export interface ReplayExport {
  schema_version: number;
  protocol: string;
  api_level: string;
  opentrons_version: string;
  source: string[];
  deck: {
    width: number;
    height: number;
    slots: {
      id: string;
      x: number;
      y: number;
      width: number;
      height: number;
    }[];
    labware: ReplayLabware[];
  };
  pipettes: { mount: string; name: string; channels: number }[];
  wells: string[];
  origins: {
    well: number;
    name: string;
    declared: boolean;
    place: string;
    volume: number | null;
    colour: string;
  }[];
  events: {
    i: number;
    op: string;
    line: number | null;
    parent: number | null;
    t: number | null;
    vol: number | null;
    targets: number[][];
    text: string;
    held: number[];
    mount?: "left" | "right" | null; // the pipette that acts; absent before export schema 3
  }[];
  initial: Record<string, WellRow>;
  deltas: ({
    wells?: Record<string, WellRow>;
    racks?: [number, string][];
    tips?: Record<string, Band[]>;
  } | null)[];
  cache_every: number;
  findings: (Finding & {
    root_event: number | null;
    well_index: number[];
    downstream_index: number[];
  })[];
  summary: {
    simulator: string;
    check: string;
    verify: string | null;
    counts: Record<string, number>;
    events: number;
  };
  verify: VerifyReport | null;
}

export interface Analysis {
  protocol: string;
  simulator: { passed: boolean; error: string | null; line: number | null };
  check: CheckReport | null;
  check_text: string | null;
  verify: VerifyReport | null;
  verify_text: string | null;
  replay: ReplayExport | null;
  prep?: PrepJson | null; // for every protocol the simulator passes; absent from analyses made before it was
  platemap_error: string | null;
  seconds: number;
}

export interface EpisodeList {
  episodes: EpisodeCard[];
  sets: string[];
  prices_read_on: string | null;
}

export class ApiError extends Error {
  status: number;
  code: string | null; // a refusal the page answers in its own way ("not_a_request")
  constructor(status: number, message: string, code: string | null = null) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let message = response.statusText;
    let code: string | null = null;
    try {
      const body = (await response.json()) as {
        detail?: string | { code?: string; message?: string };
      };
      if (typeof body.detail === "string") message = body.detail;
      else if (body.detail && typeof body.detail.message === "string") {
        message = body.detail.message;
        code = body.detail.code ?? null;
      }
    } catch {
      /* no JSON body */
    }
    throw new ApiError(response.status, message, code);
  }
  return (await response.json()) as T;
}

export interface Health {
  ok: boolean;
  opentrons: string;
  provette: string;
  episodes: number;
  live: boolean;
}

// The public repository's URL, set at build time (`VITE_REPOSITORY=https://... npm run build`).
// Empty until the repository is public: the pages then show no source link rather than a dead one.
export const REPOSITORY: string =
  (import.meta.env.VITE_REPOSITORY as string | undefined) ?? "";

export const api = {
  health: () => getJson<Health>("/health"),
  episodes: () => getJson<EpisodeList>("/api/episodes"),
  episode: (id: string) => getJson<EpisodeDetail>(`/api/episodes/${id}`),
  draft: (id: string, n: number) =>
    getJson<Draft>(`/api/episodes/${id}/drafts/${n}`),
  analysis: (id: string) => getJson<Analysis>(`/api/episodes/${id}/analysis`),
  rules: () =>
    getJson<{ schema_version: number; rules: RuleRow[] }>("/api/rules"),
  protocolUrl: (id: string) => `/api/episodes/${id}/protocol.py`,
  replayUrl: (id: string) => `/api/episodes/${id}/replay.html`,
};

/* Flow 3: check a protocol you already have (api/checks.py) */
export interface CheckRow {
  id: string;
  name: string;
  created: number;
  analysis: Analysis;
  protocol: string;
  platemap: PlateMap | null;
}

export interface PlateMapListing {
  platemaps: { id: string; request: string }[];
}

export interface ExampleProtocol {
  name: string;
  protocol: string;
  platemap_id: string;
  about: string;
}

/* One line of the Runs page's "Yours": a check this deployment kept (GET /api/checks). */
export interface CheckListRow {
  id: string;
  name: string;
  created: number;
  simulator: "passed" | "rejected";
  findings: number;
  has_map: boolean;
}

export const checks = {
  create: (body: {
    protocol: string;
    platemap: string | Record<string, unknown> | null;
    name: string;
  }) =>
    getJson<CheckRow>("/api/checks", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }),
  list: () => getJson<{ checks: CheckListRow[] }>("/api/checks"),
  get: (id: string) => getJson<CheckRow>(`/api/checks/${id}`),
  replayUrl: (id: string) => `/api/checks/${id}/replay.html`,
  protocolUrl: (id: string) => `/api/checks/${id}/protocol.py`,
  platemaps: () => getJson<PlateMapListing>("/api/platemaps"),
  platemap: (id: string) => getJson<PlateMap>(`/api/platemaps/${id}`),
  example: () => getJson<ExampleProtocol>("/api/examples/protocol"),
};

/* Flow 2: run your own (api/live.py) */
export interface LiveStatus {
  enabled: boolean;
  model: string;
  model_label: string;
  runner: string;
  runner_label: string;
  cap_usd: number;
  spent_today_usd: number;
  remaining_usd: number;
  running: number;
  examples: { id: string; technique: string | null; request: string }[];
}

export interface Planning {
  platemap: PlateMap | null;
  error: string | null;
  stop_reason: string;
  tool_calls: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number | null;
  seconds: number;
  rejections: string[];
  steps: Step[];
}

export type JobState = "running" | "done" | "failed" | "stopped"; // "stopped": by the person, before the next model call

export interface RunSnapshot extends Omit<EpisodeDetail, "done" | "outcome"> {
  state: JobState | "timeout";
  error: string | null;
  thinking: boolean;
  outcome: Outcome | null;
  done?: Record<string, unknown>;
  created?: number | null; // seconds since the epoch, when the run started
}

/* A planning job (POST /api/plans): the planner's turns as they happen, then the map. */
export interface PlanSnapshot {
  id: string;
  request: string;
  technique: string | null;
  created: number | null;
  model: string;
  model_label: string;
  state: JobState | "timeout";
  error: string | null;
  thinking: boolean;
  steps: Step[];
  platemap: PlateMap | null;
  stop_reason: string | null; // "proposed", "call budget", "stopped by the user", …
  rejections: string[];
  declined?: string | null; // the planner's sentence when it said this is not a lab request
  tool_calls: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number | null;
  seconds: number | null;
}

export interface LiveRunCard extends EpisodeCard {
  run_id: string;
  state: JobState;
  created: number | null;
}

/* One line of the Runs page's "Yours": a planning job this deployment kept (GET /api/plans). */
export interface PlanListRow {
  id: string;
  request: string;
  technique: string | null;
  created: number | null;
  state: JobState;
  outcome:
    "planning" | "proposed" | "not a request" | "no map" | "failed" | "stopped";
  tool_calls: number | null;
  cost_usd: number | null;
}

const PASSWORD_KEY = "provette.judge";

export const UNLOCK_EVENT = "provette:unlock";
export type UnlockRequest = { resolve: (unlocked: boolean) => void };

export const judge = {
  /* Open the password dialog (a 401 came back, or an action needs the password). Resolves when
     it closes: true if the tab is unlocked then, false if the reader cancelled. */
  requestUnlock: (): Promise<boolean> =>
    new Promise((resolve) =>
      window.dispatchEvent(
        new CustomEvent<UnlockRequest>(UNLOCK_EVENT, { detail: { resolve } }),
      ),
    ),
  // The key lives for the tab's session only (sessionStorage): it survives a reload, not a
  // closed tab or another browser, so a shared machine does not keep the judge's key.
  get: (): string => {
    try {
      return sessionStorage.getItem(PASSWORD_KEY) ?? "";
    } catch {
      return "";
    }
  },
  set: (value: string) => {
    try {
      sessionStorage.setItem(PASSWORD_KEY, value);
    } catch {
      /* private mode */
    }
  },
  /* Ask the server whether a password is right, before keeping it (POST /api/judge):
     "ok", "wrong", or "none" when the deployment has no password set. */
  check: async (value: string): Promise<"ok" | "wrong" | "none"> => {
    const r = await fetch("/api/judge", {
      method: "POST",
      headers: { "X-Judge-Password": value },
    });
    if (r.status === 204) return "ok";
    if (r.status === 503) return "none";
    if (r.status === 401) return "wrong";
    throw new Error(`The server answered ${r.status}`);
  },
};

/* Flow 3's memory, per tab like the judge key (sessionStorage, never localStorage): the
   composer's draft, so a half-typed check survives a tab switch, and the last check's id, so
   the Check tab comes back to it. Not a history: one draft, one id; a closed tab keeps neither. */
const DRAFT_KEY = "provette.check.draft";
const LAST_CHECK_KEY = "provette.check.last";

export interface CheckDraft {
  protocol: string;
  name: string;
  mapMode: "none" | "example" | "paste";
  mapId: string;
  mapText: string;
}

function remember(key: string, value: string | null) {
  try {
    if (value == null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, value);
  } catch {
    /* private mode */
  }
}

function recall(key: string): string | null {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

export const checkMemory = {
  draft: {
    get: (): CheckDraft | null => {
      const raw = recall(DRAFT_KEY);
      if (!raw) return null;
      try {
        return JSON.parse(raw) as CheckDraft;
      } catch {
        return null;
      }
    },
    set: (draft: CheckDraft) => remember(DRAFT_KEY, JSON.stringify(draft)),
    forget: () => remember(DRAFT_KEY, null),
  },
  last: {
    get: (): string => recall(LAST_CHECK_KEY) ?? "",
    set: (id: string) => remember(LAST_CHECK_KEY, id),
    forget: () => remember(LAST_CHECK_KEY, null),
  },
};

function withPassword(): HeadersInit {
  return {
    "content-type": "application/json",
    "x-judge-password": judge.get(),
  };
}

/* The Settings page's budgets (api/run_settings.py): for everyone on this deployment, from
   the next plan or run; changing them needs the judge key. */
export interface RunSetting {
  key: string;
  group: string;
  label: string;
  words: string;
  value: number;
  default: number;
  low: number;
  high: number;
}
export const runSettings = {
  get: () => getJson<{ settings: RunSetting[] }>("/api/run-settings"),
  save: (changes: Record<string, number>) =>
    getJson<{ settings: RunSetting[] }>("/api/run-settings", {
      method: "PUT",
      headers: withPassword(),
      body: JSON.stringify(changes),
    }),
  reset: () =>
    getJson<{ settings: RunSetting[] }>("/api/run-settings", {
      method: "DELETE",
      headers: withPassword(),
    }),
};

export const live = {
  status: () => getJson<LiveStatus>("/api/live"),
  plan: (request: string) =>
    getJson<Planning>("/api/plan", {
      method: "POST",
      headers: withPassword(),
      body: JSON.stringify({ request }),
    }),
  start: (request: string, platemap: PlateMap, technique?: string | null) =>
    getJson<{ id: string }>("/api/runs", {
      method: "POST",
      headers: withPassword(),
      body: JSON.stringify({ request, platemap, technique: technique ?? null }),
    }),
  // `anyway`: the person said to plan it though it does not read as a lab request
  startPlan: (request: string, technique?: string | null, anyway = false) =>
    getJson<{ id: string }>("/api/plans", {
      method: "POST",
      headers: withPassword(),
      body: JSON.stringify({ request, technique: technique ?? null, anyway }),
    }),
  planSnapshot: (id: string) => getJson<PlanSnapshot>(`/api/plans/${id}`),
  planEventsUrl: (id: string) => `/api/plans/${id}/events`,
  stopPlan: (id: string) =>
    getJson<{ id: string; state: string }>(`/api/plans/${id}/stop`, {
      method: "POST",
      headers: withPassword(),
    }),
  stopRun: (id: string) =>
    getJson<{ id: string; state: string }>(`/api/runs/${id}/stop`, {
      method: "POST",
      headers: withPassword(),
    }),
  /* Delete a run, a plan or a check from this deployment's history (the judge password). */
  remove: (kind: "run" | "plan" | "check", id: string) =>
    getJson<{ id: string; deleted: boolean }>(
      `/api/${kind === "run" ? "runs" : kind === "plan" ? "plans" : "checks"}/${id}`,
      { method: "DELETE", headers: withPassword() },
    ),
  plans: () => getJson<{ plans: PlanListRow[] }>("/api/plans"),
  runs: () => getJson<{ runs: LiveRunCard[] }>("/api/runs"),
  snapshot: (id: string) => getJson<RunSnapshot>(`/api/runs/${id}`),
  eventsUrl: (id: string) => `/api/runs/${id}/events`,
  analysis: (id: string) => getJson<Analysis>(`/api/runs/${id}/analysis`),
  draft: (id: string, n: number) =>
    getJson<Draft>(`/api/runs/${id}/drafts/${n}`),
  replayUrl: (id: string) => `/api/runs/${id}/replay.html`,
  protocolUrl: (id: string) => `/api/runs/${id}/protocol.py`,
};

/* The methods page's numbers (api/evidence.py), every one computed from a file under eval/. */
export interface Funnel {
  requests: number;
  pass_simulator_first: number;
  clean_first: number;
  problem_first: number;
  verified_end: number;
  repaired: number;
}

export interface Evidence {
  prices_read_on: string | null;
  prices_source: string | null;
  checks: {
    sources: string[];
    correct: { protocols: number; verified: number; wells: number };
    control: { protocols: number; verified: number };
    mutants: {
      generated: number;
      pass_simulator: number;
      equivalent: number;
      change_the_deck: number;
      caught: number;
      missed: number;
      missed_layout_swaps: number;
      sample_lost: number;
      sample_lost_caught: number;
      by_operator: {
        operator: string;
        words: string;
        generated: number;
        pass_simulator: number;
        compare_mismatch: number;
        cannot_check: number;
        accounting: number;
        prep: number;
        check: number;
        nothing: number;
        missed?: number; // of those not flagged: samples swapping wells; the rest leave the plate as asked
      }[];
    };
    hand: { protocols: number; agree: number };
  } | null;
  // The gallery's sets (PROVETTE_GALLERY_SETS), one row each in eval/agent/README.md
  agent: {
    sets: (Funnel & {
      set: string;
      model: string;
      model_label: string;
      tokens_in: number;
      tokens_out: number;
      cost_usd: number | null;
      per_verified_usd: number | null;
      stop_reasons: Record<string, number>;
      run_label: string;
      request_set: string;
      source: string;
    })[];
  };
  // The rules as text in the prompt and no checker, one draft each (eval/agent/README.md, "The baseline")
  baseline:
    | (Funnel & {
        run: string;
        model: string;
        model_label: string;
        tokens_in: number;
        tokens_out: number;
        cost_usd: number | null;
        source: string;
        broke_rule?: number; // of the drafts the simulator passed, those that broke a rule they were told
        map_mismatch?: number;
      })
    | null;
  planner: {
    requests: number;
    valid_map: number;
    agree: number;
    verify: number;
    cost_usd: number;
    tool_calls: number[];
    source: string;
  } | null;
  // eval/ledger/counts.json: Opentrons' own analysis of each run against the ledger, over the
  // public library; a fully independent reading from API 2.14 (D-10)
  ledger?: {
    library: number;
    accepted: number;
    compared: number;
    agree: number;
    independent: number;
    independent_agree: number;
    exported: number;
    events: number;
    source: string;
  } | null;
}

export const evidence = () => getJson<Evidence>("/api/evidence");

/* The documents from docs/ (api/docs.py) */
export interface DocRow {
  name: string;
  title: string;
}
export const docs = {
  list: () => getJson<{ docs: DocRow[] }>("/api/documents"),
  get: (name: string) =>
    getJson<DocRow & { markdown: string }>(`/api/documents/${name}`),
};

/* The failed-run record (api/outcomes.py) */
export interface RunOutcome {
  episode: string;
  set: string;
  when: string;
  ok: boolean;
  note: string;
  request?: string | null;
  technique?: string | null;
  model_label?: string | null;
}

export const outcomes = {
  forEpisode: (episode: string) =>
    getJson<{
      episode: string;
      latest: RunOutcome | null;
      records: RunOutcome[];
    }>(`/api/outcomes?episode=${encodeURIComponent(episode)}`),
  all: () =>
    getJson<{ records: RunOutcome[]; failures: RunOutcome[] }>("/api/outcomes"),
  record: (body: { episode: string; ok: boolean; note: string }) =>
    getJson<RunOutcome>("/api/outcomes", {
      method: "POST",
      headers: withPassword(),
      body: JSON.stringify(body),
    }),
};

/* What the checks cover for a technique (api/coverage.py, provette/rules/coverage.yaml) */
export interface Coverage {
  technique: string | null;
  matched: boolean;
  key: string | null;
  available: boolean;
  source: string | null;
  checked: string[];
  not_checked: string[];
  physics: string[];
}

export const coverage = (technique: string | null | undefined) =>
  getJson<Coverage>(
    `/api/coverage${technique ? `?technique=${encodeURIComponent(technique)}` : ""}`,
  );

export interface TechniqueCoverage {
  technique: string;
  checked: string[];
  not_checked: string[];
  physics: string[];
}
export const coverageTechniques = () =>
  getJson<{ techniques: TechniqueCoverage[]; source: string | null }>(
    "/api/coverage/techniques",
  );

/* A declared liquid no word list knows (provette/rules/roles.py `unplaced`) */
export interface UnplacedLiquid {
  name: string;
  description: string;
  wells: string[];
  line: number | null;
  sentence: string;
}

/* The word lists we own (api/roles.py) */
export interface RoleLists {
  lists: Record<string, string[]>;
  list_names: string[];
  places?: Record<string, string>;
  added_here?: Record<string, string[]>; // the words added on this deployment: only these can come out
}
export const roles = {
  get: () => getJson<RoleLists>("/api/roles"),
  add: (list: string, word: string) =>
    getJson<{
      added: { list: string; word: string };
      lists: Record<string, string[]>;
    }>(`/api/roles/${list}`, {
      method: "POST",
      headers: withPassword(),
      body: JSON.stringify({ word }),
    }),
  /* Take out a word added on this deployment; a shipped word is refused (403). */
  remove: (list: string, word: string) =>
    getJson<RoleLists & { removed: { list: string; word: string } }>(
      `/api/roles/${list}?word=${encodeURIComponent(word)}`,
      { method: "DELETE", headers: withPassword() },
    ),
};

/* Declared rules (api/declared.py, provette/rules/declared.py) */
export type DeclaredShape =
  "no_carry_over" | "full_well_not_mixed" | "add_after";
export interface DeclaredRuleData {
  id: string;
  shape: DeclaredShape;
  title: string;
  severity: Severity;
  why: string;
  fix: string;
  sources: string[];
  proposed_by: string;
  status: "proposed" | "adopted";
  adopted_on: string | null;
  [key: string]: unknown; // the shape's own fields
}
export interface SourceRow {
  key: string;
  name: string;
  url: string;
}
export interface ShapeRow {
  shape: DeclaredShape;
  words: string;
  fields: string[];
}
export interface PreviewResult {
  simulator: { passed: boolean; error: string | null; line: number | null };
  findings: Finding[];
  seconds: number;
}
export const declared = {
  sources: () =>
    getJson<{ sources: SourceRow[]; shapes: ShapeRow[] }>("/api/rules/sources"),
  addSource: (body: { key: string; name: string; url: string }) =>
    getJson<{ added: SourceRow; sources: SourceRow[]; shapes: ShapeRow[] }>(
      "/api/rules/sources",
      {
        method: "POST",
        headers: withPassword(),
        body: JSON.stringify(body),
      },
    ),
  list: () =>
    getJson<{
      rules: (DeclaredRuleData & { file: string; removable?: boolean })[];
      shapes: ShapeRow[];
    }>("/api/rules/declared"),
  /* Delete a rule added on this deployment and still proposed; a shipped or adopted one is 403. */
  remove: (id: string) =>
    getJson<{ deleted: string; rules_loaded: string[] }>(
      `/api/rules/declared/${encodeURIComponent(id)}`,
      { method: "DELETE", headers: withPassword() },
    ),
  preview: (rule: Record<string, unknown>, episode: string) =>
    getJson<PreviewResult>("/api/rules/preview", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ rule, episode }),
    }),
  save: (rule: Record<string, unknown>) =>
    getJson<{ saved: string; rule: DeclaredRuleData; rules_loaded: string[] }>(
      "/api/rules/declared",
      {
        method: "POST",
        headers: withPassword(),
        body: JSON.stringify({ rule }),
      },
    ),
};
