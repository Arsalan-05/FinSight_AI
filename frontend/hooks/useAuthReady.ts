"use client";

import { useEffect, useState } from "react";

import { isSupabaseConfigured } from "@/lib/supabase/client";
import { getAccessTokenReady } from "@/lib/supabase/session";

/** True once Supabase session is hydrated (or auth is disabled for local dev). */
export function useAuthReady(): boolean {
  const configured = isSupabaseConfigured();
  const [ready, setReady] = useState(!configured);

  useEffect(() => {
    if (!configured) return;

    let active = true;
    void getAccessTokenReady().then(() => {
      if (active) setReady(true);
    });

    return () => {
      active = false;
    };
  }, [configured]);

  return ready;
}
