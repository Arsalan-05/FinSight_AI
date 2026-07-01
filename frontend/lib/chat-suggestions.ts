/** Parse short follow-up chips from the last assistant reply. */

const BULLET_RE = /^[-•*]\s+(.+)$/;
const NUMBERED_RE = /^\d+[.)]\s+(.+)$/;

export function extractFollowUpSuggestions(text: string): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];

  const suggestions = new Set<string>();
  const lines = trimmed.split("\n").map((l) => l.trim()).filter(Boolean);

  for (const line of lines) {
    const bullet = line.match(BULLET_RE)?.[1] ?? line.match(NUMBERED_RE)?.[1];
    if (!bullet) continue;
    const candidate = bullet.replace(/\*\*/g, "").trim();
    if (candidate.length < 4 || candidate.length > 90) continue;
    if (candidate.endsWith("?") || /^(yes|no)\b/i.test(candidate)) {
      suggestions.add(candidate);
    }
  }

  const lastLine = lines[lines.length - 1] ?? "";
  const asksYesNo = /\b(yes\/no|yes or no)\b/i.test(trimmed);
  const endsWithQuestion = lastLine.endsWith("?");

  if (asksYesNo || endsWithQuestion) {
    if (![...suggestions].some((s) => /^yes\b/i.test(s))) {
      suggestions.add("Yes, please");
    }
    if (![...suggestions].some((s) => /^no\b/i.test(s))) {
      suggestions.add("No thanks");
    }
  }

  return [...suggestions].slice(0, 4);
}
