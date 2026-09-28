/**
 * Lightweight Markdown for agent replies — headings, rules, tables, lists, bold/italic/code,
 * and evidence chips. Deliberately dependency-free; covers what the advisor actually emits.
 */
import type { ReactNode } from "react";

import { splitEvidenceSegments } from "@/lib/evidence";

type OnEvidence = ((evidenceId: string) => void) | undefined;

type Block =
  | { type: "heading"; level: number; text: string }
  | { type: "rule" }
  | { type: "table"; header: string[]; rows: string[][]; align: Array<"left" | "right" | "center"> }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[]; start: number }
  | { type: "p"; lines: string[] };

const HEADING_RE = /^(#{1,6})\s+(.*)$/;
const RULE_RE = /^\s*([-*_])(\s*\1){2,}\s*$/;
const BULLET_RE = /^\s*[-•*+]\s+(.*)$/;
const ORDERED_RE = /^\s*(\d+)[.)]\s+(.*)$/;
const TABLE_SEP_RE = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;

function isTableRow(line: string): boolean {
  const t = line.trim();
  return t.startsWith("|") && t.length > 1;
}

function splitRow(line: string): string[] {
  let t = line.trim();
  if (t.startsWith("|")) t = t.slice(1);
  if (t.endsWith("|")) t = t.slice(0, -1);
  return t.split("|").map((c) => c.trim());
}

function parseBlocks(text: string): Block[] {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let para: string[] = [];

  const flush = () => {
    if (para.length) blocks.push({ type: "p", lines: para });
    para = [];
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      flush();
      continue;
    }

    const heading = trimmed.match(HEADING_RE);
    if (heading) {
      flush();
      blocks.push({ type: "heading", level: heading[1].length, text: heading[2] });
      continue;
    }

    if (RULE_RE.test(trimmed)) {
      flush();
      blocks.push({ type: "rule" });
      continue;
    }

    if (isTableRow(line) && i + 1 < lines.length && TABLE_SEP_RE.test(lines[i + 1])) {
      flush();
      const header = splitRow(line);
      const align = splitRow(lines[i + 1]).map((c) =>
        c.startsWith(":") && c.endsWith(":") ? "center" : c.endsWith(":") ? "right" : "left",
      ) as Array<"left" | "right" | "center">;
      const rows: string[][] = [];
      i += 2;
      while (i < lines.length && isTableRow(lines[i])) {
        rows.push(splitRow(lines[i]));
        i++;
      }
      i--;
      blocks.push({ type: "table", header, rows, align });
      continue;
    }

    const bullet = line.match(BULLET_RE);
    if (bullet) {
      flush();
      const items = [bullet[1]];
      while (i + 1 < lines.length && BULLET_RE.test(lines[i + 1])) {
        items.push(lines[++i].match(BULLET_RE)![1]);
      }
      blocks.push({ type: "ul", items });
      continue;
    }

    const ordered = line.match(ORDERED_RE);
    if (ordered) {
      flush();
      const items = [ordered[2]];
      while (i + 1 < lines.length && ORDERED_RE.test(lines[i + 1])) {
        items.push(lines[++i].match(ORDERED_RE)![2]);
      }
      blocks.push({ type: "ol", items, start: Number(ordered[1]) || 1 });
      continue;
    }

    para.push(line);
  }
  flush();
  return blocks;
}

export function FormatAgentText({
  text,
  onEvidenceClick,
}: {
  text: string;
  onEvidenceClick?: (evidenceId: string) => void;
}) {
  const blocks = parseBlocks(text);

  return (
    <div className="agent-md space-y-2.5">
      {blocks.map((block, i) => {
        switch (block.type) {
          case "heading": {
            const content = formatInline(block.text, onEvidenceClick);
            if (block.level <= 2) return <h3 key={i}>{content}</h3>;
            return <h4 key={i}>{content}</h4>;
          }
          case "rule":
            return <hr key={i} />;
          case "table":
            return (
              <div key={i} className="agent-md-table">
                <table>
                  <thead>
                    <tr>
                      {block.header.map((cell, j) => (
                        <th key={j} style={{ textAlign: block.align[j] ?? "left" }}>
                          {formatInline(cell, onEvidenceClick)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {block.rows.map((row, r) => (
                      <tr key={r}>
                        {block.header.map((_, j) => (
                          <td key={j} style={{ textAlign: block.align[j] ?? "left" }}>
                            {formatInline(row[j] ?? "", onEvidenceClick)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          case "ul":
            return (
              <ul key={i}>
                {block.items.map((item, j) => (
                  <li key={j}>{formatInline(item, onEvidenceClick)}</li>
                ))}
              </ul>
            );
          case "ol":
            return (
              <ol key={i} start={block.start}>
                {block.items.map((item, j) => (
                  <li key={j}>{formatInline(item, onEvidenceClick)}</li>
                ))}
              </ol>
            );
          default:
            return (
              <p key={i}>
                {block.lines.map((line, j) => (
                  <span key={j}>
                    {j > 0 && <br />}
                    {formatInline(line, onEvidenceClick)}
                  </span>
                ))}
              </p>
            );
        }
      })}
    </div>
  );
}

function formatInline(text: string, onEvidenceClick: OnEvidence): ReactNode {
  // Bold first so "**Total: [[$6,663|ev_4]]**" keeps both the emphasis and the chip.
  const parts = text.split(/(\*\*.+?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={i}>{formatSegment(part.slice(2, -2), onEvidenceClick)}</strong>;
    }
    return <span key={i}>{formatSegment(part, onEvidenceClick)}</span>;
  });
}

function formatSegment(text: string, onEvidenceClick: OnEvidence): ReactNode {
  const withEvidence = splitEvidenceTags(text, onEvidenceClick);
  return withEvidence.map((part, i) => {
    if (typeof part !== "string") return <span key={i}>{part}</span>;
    return <span key={i}>{formatEmphasis(part)}</span>;
  });
}

/** **bold**, *italic* / _italic_, `code`. */
function formatEmphasis(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*|\b_[^_\s][^_]*_\b)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return <code key={i}>{part.slice(1, -1)}</code>;
    }
    if (
      part.length > 2 &&
      ((part.startsWith("*") && part.endsWith("*")) || (part.startsWith("_") && part.endsWith("_")))
    ) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    return part;
  });
}

function splitEvidenceTags(text: string, onEvidenceClick: OnEvidence): Array<string | ReactNode> {
  const segments = splitEvidenceSegments(text);
  if (segments.length === 0) return [text];

  const out: Array<string | ReactNode> = [];
  for (const seg of segments) {
    if (seg.type === "text") {
      out.push(seg.value);
      continue;
    }
    const label = seg.amount ? `$${seg.amount}${seg.suffix}` : "source";
    out.push(
      <button
        key={`${seg.evidenceId}-${seg.raw}`}
        type="button"
        className={seg.amount ? "evidence-chip" : "evidence-chip evidence-chip-bare"}
        onClick={() => onEvidenceClick?.(seg.evidenceId)}
        title="See where this number comes from"
        aria-label={`${label} — see where this number comes from`}
      >
        {seg.amount ? label : null}
        <span className="evidence-chip-id" aria-hidden="true">ⓘ</span>
      </button>,
    );
  }
  return out.length > 0 ? out : [text];
}
