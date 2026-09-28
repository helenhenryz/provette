import type { ReactNode } from "react";
import { DISCLAIMER } from "../components/Shell";
import { LinkCard } from "../components/vocabulary";
import {
  evidence as fetchEvidence,
  REPOSITORY,
  type Evidence,
} from "../lib/api";
import { useFetch } from "../lib/useFetch";
import styles from "./About.module.css";

/* The one page of paragraphs, in the two authors' own words: why they built it, what it does, how
   (the harness around the model), what they found, what it doesn't do (the disclaimer, in full
   here), what they built, what it runs on, the licence. The numbers in "What we found" are
   computed from eval/ by the same route as Methods (GET /api/evidence), never typed here. */
/* One link each: our profiles, our universities' own sites, and the hackathon's page. */
const LINKS = {
  helen: "https://www.linkedin.com/in/helen-henryz/",
  nyle: "https://www.linkedin.com/in/nyle-hussain-b7ab05423/",
  tampere: "https://www.tuni.fi/en",
  glasgow: "https://www.gla.ac.uk/",
  hackathon: "https://nebiusglobalaihackathon.devpost.com/",
};

function Ext({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  );
}

export function AboutPage() {
  const { data } = useFetch(fetchEvidence, "evidence");
  return (
    <div className={`stack-lg ${styles.page}`}>
      <header className="stack">
        <h1>About Provette</h1>
        <p className="lead">
          Hi, we're <Ext href={LINKS.helen}>Helen</Ext> and{" "}
          <Ext href={LINKS.nyle}>Nyle</Ext>: two first-year biology students,
          one in Finland and one in Scotland.
        </p>
      </header>
      <section className="stack">
        <p>
          Helen studies at <Ext href={LINKS.tampere}>Tampere University</Ext>{" "}
          and Nyle at the <Ext href={LINKS.glasgow}>University of Glasgow</Ext>.
          We teamed up for the{" "}
          <Ext href={LINKS.hackathon}>Nebius × NVIDIA Global AI Hackathon</Ext>{" "}
          and built this across two countries and a two-hour time difference.
        </p>
      </section>
      <section className="stack">
        <h2>Why we built it</h2>
        <p>
          Robots do more and more of the pipetting in biology labs, and more of
          the scripts that drive them are being written by AI, because most
          biologists never learned to code. The robot's own simulator will tell
          you a script can run. It won't tell you whether it does your
          experiment. A protocol can pass it and still put half the volume in
          every well, or carry one patient's sample into the shared master mix
          on a used tip.
        </p>
        <p>
          Code gets tested before anyone trusts it. Lab-robot protocols never
          had anything like that, so we built it: a test suite for protocols,
          and around it a way for an AI to write ones that pass.
        </p>
      </section>
      <section className="stack">
        <h2>What it does</h2>
        <ul className={styles.does}>
          <li>
            <strong>Plans the plate.</strong> Describe the run in plain words
            and Provette drafts a plate map, what every well should end up
            holding, for you to check and edit before anything is written.
          </li>
          <li>
            <strong>Writes the protocol and proves it.</strong> Nemotron writes
            the Python; Provette replays it, follows every microlitre through
            every tip and well, and sends back what's wrong, line by line, until
            every well matches.
          </li>
          <li>
            <strong>Shows you the run.</strong> A replay of the deck in 2D and
            3D, and a prep sheet that says what to load where, and how much.
          </li>
          <li>
            <strong>Checks the protocols you already have.</strong> Paste or
            drop an OT-2 protocol and get the same report. No model involved.
          </li>
        </ul>
      </section>
      <section className="stack">
        <h2>How it works</h2>
        <p>
          Around the model we built an agent harness: the tools it can call (the
          plate map, the labware, the calculators, write, check, submit), the
          budgets it works within, and a checker that decides when the job is
          done. The model works the way a programmer works with tests: write,
          run the checks, read what failed, fix it. It never marks its own
          homework. The checks are plain code and give the same answer every
          time.
        </p>
      </section>
      {data && <Found data={data} />}
      <section className="stack">
        <h2>What it doesn't do</h2>
        <p>
          {DISCLAIMER} It can't tell how a viscous liquid behaves, whether a tip
          brushes a cell layer, or whether 0.5 µl really gets pipetted
          accurately. Every run says what wasn't looked at, under Not checked.
        </p>
      </section>
      <section className="stack">
        <h2>What we built</h2>
        <p>
          We built Provette with AI coding agents, the way Provette itself
          works: we set the goal, wrote the checks the work had to pass, and
          reviewed what came back. What that made:
        </p>
        <ul className={styles.does}>
          <li>
            <strong>The agent harness.</strong> The tools Nemotron can call, the
            budgets it works within, and the loop that sends every draft through
            the checks and back until every well is right.
          </li>
          <li>
            <strong>The ledger.</strong> Every microlitre in every tip and every
            well, followed through the run the robot's own simulator makes.
            Every check reads it.
          </li>
          <li>
            <strong>The rules.</strong> Carry-over, mixing, volumes, order of
            addition, controls, cold blocks: each in plain words, with its
            sources and its numbers, each tested on protocols that break it.
          </li>
          <li>
            <strong>The planner.</strong> Plain words in, a plate map out, for
            you to check before a line of code is written, and a gate that turns
            away what isn't a lab protocol.
          </li>
          <li>
            <strong>The replay.</strong> The whole run on the deck, in 2D and
            3D, step by step, from the same ledger.
          </li>
          <li>
            <strong>Rules without code.</strong> A form where a biologist writes
            a new rule; it runs in the very next check.
          </li>
          <li>
            <strong>The evaluation.</strong> Requests the model was never tuned
            on, a baseline with the rules in its prompt, and bugs planted in
            correct protocols, so every number on this site comes from a file.
          </li>
        </ul>
        <p>
          Every rule rests on a published source: a paper, a kit manual or a lab
          guideline, cited beside the rule. We read them, turned each into a
          check a machine can run, tested it against real protocols until it
          stopped crying wolf, and decided how much each finding matters. A rule
          without a source doesn't load. The plate maps, and the word lists that
          tell Provette what a liquid is, are ours too.
        </p>
      </section>
      <section className="stack">
        <h2>What it runs on</h2>
        <p>
          NVIDIA Nemotron 3 (Super and Nano) on Nebius Token Factory plans and
          writes the protocols; the Opentrons Python Protocol API and its
          simulator, version 8.8.2, run them, on this server or in a Token
          Factory Sandbox; Python 3.10, FastAPI and React. Our entry to the{" "}
          <Ext href={LINKS.hackathon}>Nebius × NVIDIA Global AI Hackathon</Ext>,
          Coding and Agentic Engineering track.
        </p>
        <div className={styles.more}>
          <LinkCard
            to="/docs/rulebook"
            title="The rulebook"
            words="Every rule, its numbers and its sources."
          />
          <LinkCard
            to="/methods"
            title="Methods"
            words="What we measured, and how."
          />
        </div>
      </section>
      <section className="stack">
        <h2>Licence</h2>
        <p>
          Apache-2.0.{" "}
          {REPOSITORY ? (
            <a href={REPOSITORY} target="_blank" rel="noreferrer">
              The source
            </a>
          ) : (
            "The source"
          )}{" "}
          is public at submission, and the entry is on{" "}
          <a
            href="https://nebiusglobalaihackathon.devpost.com/"
            target="_blank"
            rel="noreferrer"
          >
            the hackathon's Devpost page
          </a>
          .
        </p>
      </section>
    </div>
  );
}

/* Three results in two sentences, each from the file Methods names; the section waits for them. */
function Found({ data }: { data: Evidence }) {
  const super34 = data.agent.sets.find(
    (s) => /Super/.test(s.model_label) && !/harder/.test(s.request_set),
  );
  const nano34 = data.agent.sets.find(
    (s) => /Nano/.test(s.model_label) && !/harder/.test(s.request_set),
  );
  const m = data.checks?.mutants;
  if (!super34 || !m || !data.checks) return null;
  const changes = m.change_the_deck - (m.missed - m.missed_layout_swaps);
  const cents =
    super34.per_verified_usd != null
      ? Math.max(1, Math.round(super34.per_verified_usd * 100))
      : null;
  return (
    <section className="stack">
      <h2>What we found</h2>
      <p>
        With Provette in the loop, Nemotron Super writes a verified protocol for{" "}
        <strong>
          {super34.verified_end} of {super34.requests}
        </strong>{" "}
        requests{cents != null && <>, at about {cents} cents each</>}, against{" "}
        {super34.clean_first} on its own
        {data.baseline && (
          <>
            {" "}
            and {data.baseline.verified_end} with the same rules just written
            into its prompt
          </>
        )}
        .{nano34 && <> The much smaller Nano gets to {nano34.verified_end}.</>}{" "}
        So it's the checking we built, not knowing the rules, that does the
        work.
      </p>
      <p>
        We planted bugs in correct protocols: of the <strong>{changes}</strong>{" "}
        that change what a well ends up holding, every one of which the robot's
        simulator passed, Provette caught <strong>{m.caught}</strong>.
        {data.checks.correct.verified === data.checks.correct.protocols && (
          <>
            {" "}
            And on {data.checks.correct.protocols} correct protocols it raised
            no false alarm, across {data.checks.correct.wells.toLocaleString()}{" "}
            wells.
          </>
        )}
      </p>
    </section>
  );
}
