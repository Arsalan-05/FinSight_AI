import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";

async function readToken(): Promise<string | null> {
  const supabase = createClient();
  const { data: sessionData } = await supabase.auth.getSession();
  if (sessionData.session?.access_token) {
    return sessionData.session.access_token;
  }

  // Session cookies may not be hydrated on the first client tick after login.
  const { data: userData, error } = await supabase.auth.getUser();
  if (error || !userData.user) return null;

  const { data: refreshed } = await supabase.auth.getSession();
  return refreshed.session?.access_token ?? null;
}

export async function getAccessToken(): Promise<string | null> {
  if (!isSupabaseConfigured()) return null;
  try {
    return await readToken();
  } catch {
    return null;
  }
}

/**
 * Wait for Supabase to hydrate the browser session before protected API calls.
 * Uses onAuthStateChange so we don't race the cookie read on first paint.
 */
export async function getAccessTokenReady(maxMs = 8000): Promise<string | null> {
  if (!isSupabaseConfigured()) return null;

  const existing = await readToken();
  if (existing) return existing;

  return new Promise((resolve) => {
    const supabase = createClient();
    let settled = false;

    const finish = (token: string | null) => {
      if (settled) return;
      settled = true;
      subscription.unsubscribe();
      clearTimeout(timer);
      resolve(token);
    };

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.access_token) finish(session.access_token);
    });

    void readToken().then((token) => {
      if (token) finish(token);
    });

    const timer = setTimeout(() => finish(null), maxMs);
  });
}
