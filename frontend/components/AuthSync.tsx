"use client";

import { useEffect, useRef } from "react";

import { api } from "@/lib/api";
import { isSupabaseConfigured } from "@/lib/supabase/client";
import { getAccessTokenReady } from "@/lib/supabase/session";

/** Ensure the Supabase identity has a linked row in app `users` after login. */
export default function AuthSync() {
  const synced = useRef(false);

  useEffect(() => {
    if (!isSupabaseConfigured() || synced.current) return;

    void getAccessTokenReady().then((token) => {
      if (!token || synced.current) return;
      synced.current = true;
      void api.syncProfile().catch(() => {
        synced.current = false;
      });
    });
  }, []);

  return null;
}
