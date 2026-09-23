/** Public site origin for OAuth + post-login redirects (never use bind address 0.0.0.0). */

export function getAuthCallbackUrl(nextPath = "/"): string {
  const origin = getAuthOrigin();
  const next = nextPath.startsWith("/") ? nextPath : `/${nextPath}`;
  return `${origin}/auth/callback?next=${encodeURIComponent(next)}`;
}

/** Browser / build-time origin for OAuth redirectTo. */
export function getAuthOrigin(): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window !== "undefined") return window.location.origin;
  return "http://localhost:3000";
}

/**
 * Server-side public origin. Prefer NEXT_PUBLIC_SITE_URL, then proxy headers.
 * Avoids redirecting to http://0.0.0.0:3000 when Next listens on HOSTNAME=0.0.0.0.
 */
export function getRequestOrigin(request: Request): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "");
  if (configured) return configured;

  const forwardedHost = request.headers.get("x-forwarded-host")?.split(",")[0]?.trim();
  const hostHeader = request.headers.get("host")?.split(",")[0]?.trim();
  const host = forwardedHost || hostHeader;
  const protoHeader = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();

  if (host && !isBindAddress(host)) {
    const proto =
      protoHeader ||
      (host.startsWith("localhost") || host.startsWith("127.0.0.1") ? "http" : "https");
    return `${proto}://${host}`;
  }

  try {
    const url = new URL(request.url);
    if (!isBindAddress(url.host)) return url.origin;
  } catch {
    /* ignore */
  }

  return "http://localhost:3000";
}

function isBindAddress(host: string): boolean {
  const hostname = host.split(":")[0]?.toLowerCase() ?? "";
  return hostname === "0.0.0.0" || hostname === "[::]" || hostname === "::";
}
