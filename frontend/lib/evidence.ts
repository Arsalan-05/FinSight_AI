/** Pure helpers for agent evidence tags: ``[[$412.30|ev_17]]``. */

/**
 * Also tolerates what models actually emit: a unit after the amount
 * (``[[$3,955/mo|ev_3]]``) and bare references (``[[ev_2]]``).
 */
export const EVIDENCE_TAG_RE =
  /\[\[\s*(?:\$\s*([\d,]+(?:\.\d+)?)([^\]|]{0,16}?)\s*\|\s*)?(ev_\d+)\s*\]\]/gi;

export type EvidenceTagMatch = {
  /** Empty for bare ``[[ev_N]]`` references. */
  amount: string;
  /** Unit text after the amount, e.g. ``/mo``. */
  suffix: string;
  evidenceId: string;
  raw: string;
  index: number;
};

/** Parse all evidence tags in *text* without React dependencies. */
export function parseEvidenceTags(text: string): EvidenceTagMatch[] {
  const out: EvidenceTagMatch[] = [];
  const re = new RegExp(EVIDENCE_TAG_RE.source, EVIDENCE_TAG_RE.flags);
  let match: RegExpExecArray | null;
  while ((match = re.exec(text)) !== null) {
    out.push({
      amount: match[1] ?? "",
      suffix: (match[2] ?? "").trim(),
      evidenceId: match[3] ?? "",
      raw: match[0],
      index: match.index,
    });
  }
  return out;
}

export type EvidenceSegment =
  | { type: "text"; value: string }
  | { type: "evidence"; amount: string; suffix: string; evidenceId: string; raw: string };

/** Split *text* into plain text and evidence segments (order preserved). */
export function splitEvidenceSegments(text: string): EvidenceSegment[] {
  const tags = parseEvidenceTags(text);
  if (tags.length === 0) {
    return text ? [{ type: "text", value: text }] : [];
  }
  const out: EvidenceSegment[] = [];
  let last = 0;
  for (const tag of tags) {
    if (tag.index > last) {
      out.push({ type: "text", value: text.slice(last, tag.index) });
    }
    out.push({
      type: "evidence",
      amount: tag.amount,
      suffix: tag.suffix,
      evidenceId: tag.evidenceId,
      raw: tag.raw,
    });
    last = tag.index + tag.raw.length;
  }
  if (last < text.length) {
    out.push({ type: "text", value: text.slice(last) });
  }
  return out;
}
