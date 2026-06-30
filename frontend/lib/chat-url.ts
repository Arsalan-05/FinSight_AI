/** Build advisor chat links with an optional pre-filled prompt. */
export function chatUrl(prompt: string, options?: { send?: boolean }): string {
  const params = new URLSearchParams();
  params.set("q", prompt);
  if (options?.send !== false) {
    params.set("send", "1");
  }
  return `/chat?${params.toString()}`;
}

/** Extract a quoted question from insight card action copy. */
export function promptFromInsightAction(action: string): string {
  const quoted = action.match(/['"]([^'"]+)['"]/);
  if (quoted?.[1]) return quoted[1];
  const stripped = action.replace(/^(review in chat|ask):\s*/i, "").trim();
  return stripped || action;
}
