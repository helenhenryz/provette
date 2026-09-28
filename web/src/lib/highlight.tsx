import { Fragment } from "react";
import { normalizeTokens, Prism } from "prism-react-renderer";
import styles from "./highlight.module.css";

/* Source code as coloured tokens, one array per line, with Prism's own grammars (python, yaml,
   json). The colours are the page's tokens (--code-*), so both themes read them; an unknown
   language comes back as plain text. */

export type Language = "python" | "yaml" | "json";

export interface CodeToken {
  types: string[];
  content: string;
  empty?: boolean;
}

export function codeLines(
  text: string,
  language: Language = "python",
): CodeToken[][] {
  const body = text.replace(/\n$/, "");
  const grammar = Prism.languages[language];
  if (!grammar)
    return body
      .split("\n")
      .map((line) => [{ types: ["plain"], content: line }]);
  return tokenLines(body, language);
}

/* Prism's lines, with the marker it puts on an empty line (a token holding "\n") taken out: the
   caller writes the line breaks, and a second one would double every blank line. */
function tokenLines(text: string, language: Language): CodeToken[][] {
  const grammar = Prism.languages[language];
  return normalizeTokens(Prism.tokenize(text, grammar)).map((line) =>
    line.filter((t) => !t.empty && t.content !== "\n"),
  );
}

const KINDS = [
  "comment",
  "string",
  "keyword",
  "number",
  "boolean",
  "function",
  "builtin",
  "class-name",
  "decorator",
  "operator",
  "punctuation",
  "key",
  "atrule",
];

function kindOf(types: string[]): string | undefined {
  for (let i = types.length - 1; i >= 0; i--)
    if (KINDS.includes(types[i])) return types[i];
  return undefined;
}

/* One line's tokens as spans; an empty line keeps its height. */
export function CodeLine({ tokens }: { tokens: CodeToken[] }) {
  if (tokens.length === 0 || tokens.every((t) => t.content === ""))
    return <> </>;
  return (
    <>
      {tokens.map((t, i) => {
        const kind = kindOf(t.types);
        return kind ? (
          <span key={i} className={styles[kind.replace("-", "_")]}>
            {t.content}
          </span>
        ) : (
          <span key={i}>{t.content}</span>
        );
      })}
    </>
  );
}

/* A wrapped line continues under its own indentation, two columns in, as a code editor wraps:
   the style for the line's cell, from its leading spaces. */
export function hangingIndent(tokens: CodeToken[]): React.CSSProperties {
  const text = tokens.map((t) => t.content).join("");
  const lead = /^[ \t]*/.exec(text)?.[0] ?? "";
  const n = [...lead].reduce((w, c) => w + (c === "\t" ? 4 : 1), 0) + 2;
  return { paddingLeft: `calc(${n}ch + var(--s-3))`, textIndent: `-${n}ch` };
}

/* The whole text as coloured spans, newlines kept exactly: what an editor lays under its text box
   (the characters must match the text box's one for one, so an empty line stays empty). */
export function highlightNode(
  text: string,
  language: Language = "python",
): React.ReactNode {
  const grammar = Prism.languages[language];
  if (!grammar) return text;
  const lines = tokenLines(text, language);
  return lines.map((tokens, i) => (
    <Fragment key={i}>
      {tokens.map((t, j) => {
        const kind = kindOf(t.types);
        return kind ? (
          <span key={j} className={styles[kind.replace("-", "_")]}>
            {t.content}
          </span>
        ) : (
          t.content
        );
      })}
      {i < lines.length - 1 ? "\n" : ""}
    </Fragment>
  ));
}
