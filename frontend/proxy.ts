import { type NextRequest } from "next/server";

import { updateSession } from "@/lib/supabase/session-proxy";

export async function proxy(request: NextRequest) {
  return updateSession(request);
}

export const config = {
  matcher: [
    /*
     * Skip static assets and the same-origin API proxy (/backend/*).
     * Proxy traffic must not go through the Supabase session refresh.
     */
    "/((?!_next/static|_next/image|backend/|favicon.ico|icon(?:$|\\?)|apple-icon(?:$|\\?)|manifest\\.webmanifest|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
