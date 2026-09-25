"use client";

import { useEffect, useState } from "react";

import { getAccessTokenReady } from "@/lib/supabase/session";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";

/**
 * True once a Supabase JWT is available.
 * Does NOT wait for bootstrap — dashboard loads data in one /dashboard call.
 */
export function useAuthReady(): boolean {
  const configured = isSupabaseConfigured();
  const [ready, setReady] = useState(!configured);

  useEffect(() => {
    if (!configured) return;

    let active = true;

    async function waitForSession() {
      const token = await getAccessTokenReady();
      if (active) setReady(Boolean(token));
    }

    void waitForSession();

    const supabase = createClient();
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!active) return;
      setReady(Boolean(session?.access_token));
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, [configured]);

  return ready;
}
