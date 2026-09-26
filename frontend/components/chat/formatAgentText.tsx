/** Lightweight formatting for agent replies — paragraphs, bullets, bold, evidence chips. */
import type { ReactNode } from "react";

import { splitEvidenceSegments } from "@/lib/evidence";

export function FormatAgentText({
  text,
  onEvidenceClick,
}: {
  text: string;
  onEvidenceClick?: (evidenceId: string) => void;
}) {
  const blocks = text.split(/\n\n+/);

  return (
    <div className="space-y-2.5">
      {blocks.map((block, i) => {
        const lines = block.split("\n");
        const isList = lines.every((l) => /^[-•*]\s/.test(l.trim()) || l.trim() === "");

        if (isList && lines.some((l) => l.trim())) {
          return (
            <ul key={i}>
              {lines
                .filter((l) => l.trim())
                .map((line, j) => (
                  <li key={j}>{formatInline(line.replace(/^[-•*]\s*/, ""), onEvidenceClick)}</li>
                ))}
            </ul>
          );
        }

        return (
          <p key={i}>
            {lines.map((line, j) => (
              <span key={j}>
                {j > 0 && <br />}
                {formatInline(line, onEvidenceClick)}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}

function formatInline(
  text: string,
  onEvidenceClick?: (evidenceId: string) => void,
): ReactNode {
  const withEvidence = splitEvidenceTags(text, onEvidenceClick);
  return withEvidence.map((part, i) => {
    if (typeof part !== "string") return <span key={i}>{part}</span>;
    return <span key={i}>{formatBold(part)}</span>;
  });
}

function formatBold(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function splitEvidenceTags(
  text: string,
  onEvidenceClick?: (evidenceId: string) => void,
): Array<string | ReactNode> {
  const segments = splitEvidenceSegments(text);
  if (segments.length === 0) return [text];

  const out: Array<string | ReactNode> = [];
  for (const seg of segments) {
    if (seg.type === "text") {
      out.push(seg.value);
      continue;
    }
    out.push(
      <button
        key={`${seg.evidenceId}-${seg.raw}`}
        type="button"
        className="evidence-chip"
        onClick={() => onEvidenceClick?.(seg.evidenceId)}
        title="See where this number comes from"
        aria-label={`$${seg.amount} — see where this number comes from`}
      >
        {`$${seg.amount}`}
        <span className="evidence-chip-id" aria-hidden="true">ⓘ</span>
      </button>,
    );
  }
  return out.length > 0 ? out : [text];
}
