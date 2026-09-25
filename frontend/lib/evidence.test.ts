/**
 * Evidence tag parsing — skipped until Vitest is added to package.json.
 *
 * Enable with:
 *   npm i -D vitest
 *   // package.json → "test": "vitest run"
 *   // then remove .skip below and assert against parseEvidenceTags /
 *   // splitEvidenceSegments from ./evidence
 *
 * Expected cases:
 * - "Spent [[$412.30|ev_17]] on rent" → amount 412.30, id ev_17
 * - "no tags" → []
 * - "A [[$1.00|ev_1]] B" → text / evidence / text segments
 */

export {};

// Intentionally empty — Vitest not installed. See docs/e2e-checklist.md for
// related frontend smoke coverage.
