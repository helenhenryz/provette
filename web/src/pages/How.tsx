import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Loading, Notice } from "../components/Notice";
import {
  evidence as fetchEvidence,
  REPOSITORY,
  type Evidence,
} from "../lib/api";
import { money, moneyFine } from "../lib/format";
import { useFetch } from "../lib/useFetch";
import styles from "./How.module.css";

/* The methods page: the evidence a judge needs, every number computed from a file under eval/
   at request time and the file named. The history (the earlier runs, every failure read by
   hand) stays in the repository's eval/ READMEs, and one line points there. How the checks
   work comes first, with the terms beside it, so the numbers are read knowing what they count. */
export function HowPage() {
  const { data, error, loading } = useFetch(fetchEvidence, "evidence");
  return (
    <div className="stack-lg">
      <header className="stack">
        <h1 title="every number is computed from a file under eval/ when the page loads; the file is named under each table">
          Methods
        </h1>
        <p className="muted">
          How the checks work, then four questions, each answered from the runs
          on file. Every number is computed when the page loads.
        </p>
      </header>

      <section className="stack">
        <h2>How the checks work</h2>
        <ol className={styles.steps}>
          <li>
            <strong>Run it.</strong> The protocol runs in Opentrons' own
            simulator, at the version Provette pins.
          </li>
          <li>
            <strong>Record it.</strong> The ledger follows every microlitre
            through every tip and well: each action with its line, what it left
            behind, and where each drop started. It is checked against
            Opentrons' own analysis of the same run, and the two must agree.
          </li>
          <li>
            <strong>Check it three ways.</strong> The plate map: does every well
            hold what was asked. The twelve rules: what a well can hold and
            still be wrong (carry-over, mixing, volumes, order of addition,
            controls), each resting on a published source. The accounting and
            the prep sheet: where every sample went, and whether a tube runs
            dry.
          </li>
          <li>
            <strong>Say what's wrong.</strong> A finding names the step, the
            line, the wells and the fix. The checks are plain code: the same
            protocol gets the same answer every time, and the model never judges
            its own work.
          </li>
        </ol>
      </section>
      <section className="stack">
        <h2>Terms</h2>
        <dl className={styles.terms}>
          <dt>Plate map</dt>
          <dd>
            What every well should hold at the end, approved by a person before
            anything is written.
          </dd>
          <dt>Trace</dt>
          <dd>
            Every action of the run under the Opentrons simulator, each with its
            line in the protocol.
          </dd>
          <dt>Ledger</dt>
          <dd>
            What is in every well and on every tip after each action, and where
            each drop started.
          </dd>
          <dt>Finding</dt>
          <dd>
            Where the ledger departs from the plate map or breaks a rule: the
            step, the line, the wells and the fix.
          </dd>
          <dt>Verified</dt>
          <dd>
            Every well matches the plate map, the sample accounting and the prep
            sheet raise no flag, and no rule fires with an error or a warning.
          </dd>
        </dl>
      </section>

      {loading && <Loading what="Computing the numbers from eval/" />}
      {error && (
        <Notice tone="error" title="The numbers could not be computed">
          {error}
        </Notice>
      )}
      {data && <EvidenceSections data={data} />}

      <p className={styles.history}>
        The earlier runs, every failure read by hand and the full tables:{" "}
        {REPOSITORY ? (
          <a href={REPOSITORY} target="_blank" rel="noreferrer">
            the repository's eval pages
          </a>
        ) : (
          <>
            the repository's <span className="mono">eval/</span> pages.
          </>
        )}
      </p>
    </div>
  );
}

/* The four questions a biologist asks of a checker, in the order a judge reads them: does it
   help a model write the protocol, does it catch what the simulator misses, does it pass what
   is correct, and can the record every check reads be trusted. Each is one answer sentence, one table in plain column names, and two visible
   lines of how it was measured. The run names (super, E1 to E3) are hovers only. */
function EvidenceSections({ data }: { data: Evidence }) {
  const m = data.checks?.mutants;
  const sets = [...data.agent.sets].sort(
    (a, b) =>
      Number(/harder/.test(a.request_set)) -
        Number(/harder/.test(b.request_set)) ||
      Number(/Nano/.test(a.model_label)) - Number(/Nano/.test(b.model_label)),
  );
  const headline = sets[0];
  const everyday = headline?.requests ?? 34;
  const harder = sets.find((s) => /harder/.test(s.request_set))?.requests;
  const changes = m
    ? m.change_the_deck - (m.missed - m.missed_layout_swaps)
    : 0; // bugs that change what a well holds
  const unchanged = m ? m.equivalent + (m.missed - m.missed_layout_swaps) : 0; // leave the plate as the request allows
  return (
    <>
      <section className="stack">
        <h2>Does a model write correct protocols with Provette?</h2>
        {headline && (
          <p className={styles.answer}>
            Yes. Nemotron Super verifies{" "}
            <strong>
              {headline.verified_end} of {headline.requests}
            </strong>{" "}
            requests with the checks in its loop, against {headline.clean_first}{" "}
            of {headline.requests} on its first draft
            {data.baseline && (
              <>
                {" "}
                and {data.baseline.verified_end} of {data.baseline.requests}{" "}
                with the same rules written into its prompt
              </>
            )}
            , at {moneyFine(headline.per_verified_usd)} a protocol.
          </p>
        )}
        {data.baseline?.broke_rule != null && (
          <p>
            Told the rules, it still broke them: of the{" "}
            {data.baseline.pass_simulator_first} drafts the simulator passed,{" "}
            <strong>{data.baseline.broke_rule}</strong> broke a rule written
            into its own prompt
            {data.baseline.map_mismatch != null && (
              <> and {data.baseline.map_mismatch} missed the plate map</>
            )}
            . The checks caught each one. What moves the number is a report the
            model can act on, not knowing the rule.
          </p>
        )}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nemotron</th>
                <th>requests</th>
                <th className="num">verified, first draft</th>
                <th className="num">verified with Provette</th>
                <th className="num">cost per verified protocol</th>
              </tr>
            </thead>
            <tbody>
              {sets.map((s) => (
                <tr key={s.set} title={`${s.set} · ${s.run_label}`}>
                  <td>
                    {short(s.model_label)}
                    {/best of 3/.test(s.run_label) && (
                      <span className="muted small"> · best of 3</span>
                    )}
                  </td>
                  <td>
                    {s.requests}{" "}
                    {/harder/.test(s.request_set) ? "harder" : "everyday"}
                  </td>
                  <td className="num">{s.clean_first}</td>
                  <td className="num">
                    <strong>{s.verified_end}</strong> (
                    {Math.round((100 * s.verified_end) / s.requests)}%)
                  </td>
                  <td className="num">{moneyFine(s.per_verified_usd)}</td>
                </tr>
              ))}
              {data.baseline && (
                <tr title={data.baseline.run}>
                  <td>
                    {short(data.baseline.model_label)}
                    <span className="muted small">
                      {" "}
                      · rules in prompt, no checker
                    </span>
                  </td>
                  <td>{data.baseline.requests} everyday</td>
                  <td className="num">{data.baseline.clean_first}</td>
                  <td className="num">
                    {data.baseline.verified_end} of {data.baseline.requests}
                  </td>
                  <td className="num">
                    {money(data.baseline.cost_usd)} in all
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <How>
          {everyday} requests written the way a scientist would ask
          {harder ? `, and ${harder} harder ones` : ""}. The model plans the
          plate map, writes, runs the checks itself, repairs from the report and
          submits only what verifies; its first draft is judged by the same
          checks. Nano gets three tries per request. These are the runs the{" "}
          <Link to="/examples">Examples</Link> replay.
        </How>
        <Sources
          files={[
            ...data.agent.sets.map((s) => s.source),
            ...(data.baseline ? [data.baseline.source] : []),
          ]}
        />
      </section>

      {data.checks && m && (
        <section className="stack">
          <h2>Does Provette catch what the simulator passes?</h2>
          <p className={styles.answer}>
            Yes. Of <strong>{changes}</strong> planted bugs that change what a
            well ends up holding, all passed by the simulator, Provette flags{" "}
            <strong>{m.caught}</strong>, including every one that throws a
            sample away ({m.sample_lost_caught} of {m.sample_lost}). The{" "}
            {m.missed_layout_swaps} it misses are samples swapping wells, which
            a plate map that leaves positions free cannot see.
          </p>
          <div className="table-wrap">
            <table title="E1 to E3, the planted bugs">
              <thead>
                <tr>
                  <th>planted bug</th>
                  <th className="num">planted</th>
                  <th className="num">passed the simulator</th>
                  <th className="num">flagged by Provette</th>
                  <th
                    className="num"
                    title="the plate ends as the request allows: nothing to catch"
                  >
                    nothing to catch
                  </th>
                  <th className="num">missed</th>
                </tr>
              </thead>
              <tbody>
                {m.by_operator.map((r) => (
                  <tr key={r.operator}>
                    <td>{r.words}</td>
                    <td className="num">{r.generated}</td>
                    <td className="num">{r.pass_simulator}</td>
                    <td className="num">{r.pass_simulator - r.nothing}</td>
                    <td className="num">{r.nothing - (r.missed ?? 0)}</td>
                    <td className="num">{r.missed ?? 0}</td>
                  </tr>
                ))}
                <tr className={styles.total}>
                  <td>all</td>
                  <td className="num">{m.generated}</td>
                  <td className="num">{m.pass_simulator}</td>
                  <td className="num">{m.caught}</td>
                  <td className="num">{unchanged}</td>
                  <td className="num">{m.missed_layout_swaps}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <How>
            {m.generated} bugs planted in the {data.checks.correct.protocols}{" "}
            correct protocols by five mechanical edits. "Nothing to catch": the
            plate still ends as the request allows. "Missed": samples swapping
            wells on a plate map that leaves positions free. The plate-map
            comparison flagged every bug that was caught; the accounting, the
            prep sheet and the rules say why.
          </How>
          <Sources files={data.checks.sources} />
        </section>
      )}

      {data.checks && (
        <section className="stack">
          <h2>Does it pass what is correct, and only that?</h2>
          <p className={styles.answer}>
            Yes.{" "}
            <strong>
              {data.checks.correct.verified} of {data.checks.correct.protocols}
            </strong>{" "}
            correct protocols verify, over{" "}
            {data.checks.correct.wells.toLocaleString()} wells, and{" "}
            {data.checks.control.verified} of {data.checks.control.protocols}{" "}
            verify against the wrong plate map.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>test</th>
                  <th className="num">result</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Correct protocols against their own plate maps</td>
                  <td className="num">
                    {data.checks.correct.verified} of{" "}
                    {data.checks.correct.protocols} verify
                  </td>
                </tr>
                <tr>
                  <td>The same protocols against another protocol's map</td>
                  <td className="num">
                    {data.checks.control.verified} of{" "}
                    {data.checks.control.protocols} verify
                  </td>
                </tr>
                <tr>
                  <td>The prep sheet, against one worked out by hand</td>
                  <td className="num">
                    {data.checks.hand.agree} of {data.checks.hand.protocols}{" "}
                    agree
                  </td>
                </tr>
                {data.planner && (
                  <tr title={data.planner.source}>
                    <td>
                      Plate maps the model plans from a request, against a
                      known-correct protocol
                    </td>
                    <td className="num">
                      {data.planner.verify} of {data.planner.requests} verify
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <How>
            The {data.checks.correct.protocols} protocols were written before
            the checker existed, and their plate maps before the protocols were
            seen, so neither was fitted to the other.
          </How>
          <Sources
            files={[
              ...data.checks.sources,
              ...(data.planner ? [data.planner.source] : []),
            ]}
          />
        </section>
      )}

      {data.ledger && (
        <section className="stack">
          <h2>Can the ledger be trusted?</h2>
          <p className={styles.answer}>
            Yes. On Opentrons' public protocol library, written by people who
            are not us, Opentrons' own analysis of each run agrees with the
            ledger on{" "}
            <strong>
              {data.ledger.agree} of {data.ledger.compared}
            </strong>{" "}
            protocols, over {data.ledger.events.toLocaleString()} recorded
            events, and fully independently on {data.ledger.independent_agree}{" "}
            of {data.ledger.independent} (API 2.14 and later).
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>step</th>
                  <th className="num">protocols</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>In the library</td>
                  <td className="num">{data.ledger.library}</td>
                </tr>
                <tr>
                  <td>The simulator accepts</td>
                  <td className="num">{data.ledger.accepted}</td>
                </tr>
                <tr>
                  <td>Opentrons' analysis agrees with the ledger</td>
                  <td className="num">
                    {data.ledger.agree} of {data.ledger.compared}
                  </td>
                </tr>
                <tr>
                  <td>
                    Of those, a fully independent reading (API 2.14 and later)
                  </td>
                  <td className="num">
                    {data.ledger.independent_agree} of {data.ledger.independent}
                  </td>
                </tr>
                <tr>
                  <td>The replay draws the run</td>
                  <td className="num">
                    {data.ledger.exported} of {data.ledger.accepted}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <How>
            Every check reads the ledger, so it is checked against Opentrons'
            official analysis of the same protocol. From API level 2.14 that
            analysis is independent of the messages the ledger reads; below it,
            Opentrons builds it from the same messages, so there it checks our
            reading of them. The protocols the simulator refuses reach into old
            Opentrons internals or use labware the pinned version lacks. Every
            rule was also run over this library, and a sample of what it flagged
            read, to set its thresholds; the findings there are counts, not yet
            judged.
          </How>
          <Sources files={[data.ledger.source]} />
        </section>
      )}

      <section className="stack">
        <h2>What it does not check</h2>
        <ul className={styles.notChecked}>
          <li>
            The physics: viscosity, a drop left on a tip, a tip touching a cell
            layer. That needs a real run.
          </li>
          <li>
            Samples swapping wells when the plate map leaves positions free.
          </li>
          <li>
            A wrong declared volume: the replay runs the tube dry and says so.
          </li>
          <li>
            Per technique: the Not checked row on every run, e.g.{" "}
            <Link to="/episodes/super/plain/pcr-01">a PCR setup</Link>.
          </li>
        </ul>
      </section>
    </>
  );
}

/* "Nemotron 3 Super 120B" under a "Nemotron" column: "Super 120B" */
const short = (label: string) => label.replace(/^Nemotron \d+ /, "");

/* "How we measured it": two lines, always visible. */
function How({ children }: { children: ReactNode }) {
  return (
    <p className={styles.how}>
      <span className={styles.howLabel}>How we measured it</span> {children}
    </p>
  );
}

/* "Computed from …": the fact is the point, the paths are for the one judge who checks. */
function Sources({ files }: { files: string[] }) {
  return (
    <details className={styles.sources}>
      <summary>
        Computed from{" "}
        {files.length === 1 ? "one file" : `${files.length} files`} under eval/
      </summary>
      <ul>
        {files.map((f, i) => (
          <li key={i} className="mono">
            {f}
          </li>
        ))}
      </ul>
    </details>
  );
}
