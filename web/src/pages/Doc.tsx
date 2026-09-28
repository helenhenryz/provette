import { marked } from "marked";
import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { Loading, Notice } from "../components/Notice";
import { docs } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import styles from "./Doc.module.css";

/* A document from docs/, rendered: the rulebook, the learning guide, what they link to. The
   text is the repository's own, so it is rendered as written; a link to another document in
   the same folder becomes a link to its page here. */
export function DocPage() {
  const { name = "" } = useParams();
  const doc = useFetch(() => docs.get(name), `doc:${name}`);
  const rendered = useMemo(
    () => (doc.data ? render(doc.data.markdown) : { html: "", toc: [] }),
    [doc.data],
  );
  const { html, toc } = rendered;
  if (doc.loading) return <Loading what="Loading the document" />;
  if (doc.error || !doc.data)
    return (
      <Notice
        tone="error"
        title={
          doc.status === 404
            ? "No such document"
            : "The document could not be loaded"
        }
      >
        {doc.error && doc.error.toLowerCase() !== "no such document" && (
          <>{doc.error} · </>
        )}
        <Link to="/rules">Rules</Link>
      </Notice>
    );
  return (
    <article className={styles.page}>
      <div className={styles.doc}>
        <p className={styles.crumbs}>
          <Link to="/rules">Rules</Link> <span className="faint">/</span>{" "}
          <span className="muted">{doc.data.title}</span>
          <span className={styles.source}>docs/{doc.data.name}.md</span>
        </p>
        {toc.length > 2 && (
          <details className={styles.tocFold}>
            <summary>On this page</summary>
            <Toc toc={toc} />
          </details>
        )}
        <div
          className={styles.body}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </div>
      {toc.length > 2 && (
        <nav className={styles.tocSide} aria-label="On this page">
          <div className={styles.tocTitle}>On this page</div>
          <Toc toc={toc} />
        </nav>
      )}
    </article>
  );
}

function Toc({ toc }: { toc: { id: string; text: string }[] }) {
  return (
    <ol className={styles.toc}>
      {toc.map((h) => (
        <li key={h.id}>
          <a href={`#${h.id}`}>{h.text}</a>
        </li>
      ))}
    </ol>
  );
}

/* A slug for a heading, the way GitHub makes one, so links written in the Markdown keep working. */
function slug(text: string): string {
  return text
    .toLowerCase()
    .replace(/<[^>]+>/g, "")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

function render(markdown: string): {
  html: string;
  toc: { id: string; text: string }[];
} {
  const toc: { id: string; text: string }[] = [];
  const r = new marked.Renderer();
  const baseLink = marked.Renderer.prototype.link;
  r.link = function (token) {
    // `rule-sources.md` or `rule-sources.md#anchor` -> `/docs/rule-sources#anchor`
    const m = /^([a-z0-9-]+)\.md(#.*)?$/.exec(token.href);
    if (m) token.href = `/docs/${m[1]}${m[2] ?? ""}`;
    return baseLink.call(this, token);
  };
  r.heading = function (token) {
    const text = this.parser.parseInline(token.tokens);
    const id = slug(token.text);
    if (token.depth === 2)
      toc.push({ id, text: token.text.replace(/[`*_]/g, "") });
    return `<h${token.depth} id="${id}">${text}</h${token.depth}>\n`;
  };
  const html = marked.parse(markdown, {
    renderer: r,
    gfm: true,
    breaks: false,
  }) as string;
  return { html, toc };
}
