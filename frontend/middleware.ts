import { type NextRequest } from "next/server";

import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  return updateSession(request);
}

export const config = {
  matcher: [
    /*
     * Skip static assets and the same-origin API proxy (/backend/*).
     * Proxy traffic must not go through Supabase session middleware.
     */
    "/((?!_next/static|_next/image|backend/|favicon.ico|icon(?:$|\\?)|apple-icon(?:$|\\?)|manifest\\.webmanifest|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
