/** Lightweight formatting for agent replies — paragraphs, bullets, bold. */
import type { ReactNode } from "react";

export function FormatAgentText({ text }: { text: string }) {
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
                  <li key={j}>{formatInline(line.replace(/^[-•*]\s*/, ""))}</li>
                ))}
            </ul>
          );
        }

        return (
          <p key={i}>
            {lines.map((line, j) => (
              <span key={j}>
                {j > 0 && <br />}
                {formatInline(line)}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}

function formatInline(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}
