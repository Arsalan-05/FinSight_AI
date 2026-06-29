"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";
import { getAccessTokenReady } from "@/lib/supabase/session";

/**
 * True once Supabase JWT is available and /auth/sync has run.
 * Prevents protected API calls before the session cookie hydrates.
 */
export function useAuthReady(): boolean {
  const configured = isSupabaseConfigured();
  const [ready, setReady] = useState(!configured);

  useEffect(() => {
    if (!configured) return;

    let active = true;

    async function bootstrap() {
      const token = await getAccessTokenReady();
      if (!active) return;
      if (!token) {
        setReady(false);
        return;
      }
      try {
        await api.syncProfile();
      } catch {
        // Sync can fail if DB is briefly unavailable — still allow data fetch + retry
      }
      if (active) setReady(true);
    }

    void bootstrap();

    const supabase = createClient();
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!active) return;
      if (session?.access_token) {
        void api.syncProfile().finally(() => {
          if (active) setReady(true);
        });
      } else {
        setReady(false);
      }
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, [configured]);

  return ready;
}
