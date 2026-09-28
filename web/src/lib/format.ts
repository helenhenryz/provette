/* Numbers and words, always with their unit. */

export function money(usd: number | null | undefined): string {
  if (usd == null) return "cost not recorded";
  if (usd === 0) return "$0.00";
  if (usd < 0.01) return `${(usd * 100).toFixed(1)} ¢`;
  return `$${usd.toFixed(2)}`;
}

/* A cost per protocol, to the tenth of a cent: what eval/agent/README.md's tables print. */
export function moneyFine(usd: number | null | undefined): string {
  if (usd == null) return "—";
  return `$${usd.toFixed(3)}`;
}

export function seconds(s: number | null | undefined): string {
  if (s == null) return "";
  if (s < 60) return `${Math.round(s)} s`;
  const m = Math.floor(s / 60);
  const r = Math.round(s - m * 60);
  return `${m} min ${r} s`;
}

export function ul(v: number | null | undefined): string {
  if (v == null) return "?";
  const n = Math.abs(v) >= 100 ? Math.round(v) : Math.round(v * 10) / 10;
  return `${n} µl`;
}

/* "23 Sep 2026, 22:36", in the reader's own time zone. `t` is seconds since the epoch, or ISO. */
export function when(t: number | string): string {
  const d = typeof t === "number" ? new Date(t * 1000) : new Date(t);
  if (Number.isNaN(d.getTime())) return String(t);
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  const two = (n: number) => String(n).padStart(2, "0");
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}, ${two(d.getHours())}:${two(d.getMinutes())}`;
}

export function tokens(n: number | null | undefined): string {
  if (n == null) return "";
  if (n >= 1000) return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k`;
  return String(n);
}

export function plural(n: number, word: string, plural?: string): string {
  return `${n} ${n === 1 ? word : (plural ?? `${word}s`)}`;
}

/* The first clause of a request, short: "Set up PCR reactions for…". A chip and a card show
   this; the whole request is their `title`. */
export function gist(request: string): string {
  const first = request.split(/[.;](?:\s|$)/)[0].trim();
  const words = first.split(/\s+/);
  return words.length > 5 ? words.slice(0, 5).join(" ") + "…" : first;
}

/* "sample_3" -> "sample 3", "master_mix" -> "master mix", "template@A1" -> "template from A1" */
export function liquidName(logical: string): string {
  return logical.replace("@", " from ").replace(/_/g, " ");
}

/* The simulator row's hover: the version is pinned, so it is said once here and not beside
   the verdict, where a number reads as a score. Without a version at hand (a draft still
   running), the sentence points at the foot of the page, which shows it. */
export function simulatorTitle(version?: string | null): string {
  return version
    ? `Opentrons simulator ${version} (the version Provette pins)`
    : "Opentrons simulator (the version Provette pins is at the foot of the page)";
}
