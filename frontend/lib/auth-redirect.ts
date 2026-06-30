/** OAuth return URL — use NEXT_PUBLIC_SITE_URL in dev so Supabase allow-list matches. */
export function getAuthCallbackUrl(nextPath = "/"): string {
  const origin = getAuthOrigin();
  const next = nextPath.startsWith("/") ? nextPath : `/${nextPath}`;
  return `${origin}/auth/callback?next=${encodeURIComponent(next)}`;
}

function getAuthOrigin(): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window !== "undefined") return window.location.origin;
  return "http://localhost:3000";
}
