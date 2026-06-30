"use client";

import { Loader2, Mail } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Logo } from "@/components/brand/Logo";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";

function LoginForm() {
  const searchParams = useSearchParams();
  const urlError = searchParams.get("error");
  const [loading, setLoading] = useState<"google" | "email" | null>(null);
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(
    urlError ? "Sign-in failed. Please try again." : null,
  );
  const configured = isSupabaseConfigured();

  const redirectTo = () => {
    const next = searchParams.get("next") ?? "/";
    return `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`;
  };

  const signInWithGoogle = async () => {
    if (!configured) return;
    setLoading("google");
    setAuthError(null);
    setMessage(null);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: redirectTo() },
      });
      if (error) {
        setAuthError(
          error.message.toLowerCase().includes("not enabled")
            ? "Google sign-in isn't available right now. Try email instead."
            : "We couldn't start Google sign-in. Please try again.",
        );
      }
    } finally {
      setLoading(null);
    }
  };

  const signInWithEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!configured || !email.trim()) return;
    setLoading("email");
    setAuthError(null);
    setMessage(null);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithOtp({
        email: email.trim(),
        options: { emailRedirectTo: redirectTo() },
      });
      if (error) {
        setAuthError("We couldn't send that link. Check your email and try again.");
      } else {
        setMessage(`Check your inbox — we sent a sign-in link to ${email.trim()}.`);
      }
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="flex min-h-screen">
      <div className="mesh-bg" aria-hidden />

      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden p-12 lg:flex">
        <div className="absolute inset-0 bg-gradient-to-br from-teal-700/20 via-transparent to-blue-800/10" />
        <div className="relative">
          <Logo size={44} subtitle="Personal Finance" />
        </div>

        <div className="relative max-w-md space-y-6">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight">
            Your finances,
            <span className="text-gradient"> understood.</span>
          </h1>
          <p className="text-base leading-relaxed text-[var(--muted)]">
            See where your money goes, search transactions in plain English, and get
            guidance from an advisor that knows your real spending.
          </p>
          <div className="flex flex-wrap gap-2">
            {["Spending insights", "Smart search", "Personal advisor"].map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-xs text-[var(--muted)]"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-[var(--muted)]">
          Private by design · Your data stays yours
        </p>
      </div>

      <div className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-md space-y-8">
          <div className="space-y-4 text-center lg:text-left">
            <div className="mx-auto lg:mx-0">
              <Logo size={48} compact subtitle="" />
            </div>
            <div className="space-y-2">
              <h2 className="text-2xl font-semibold tracking-tight">Welcome back</h2>
              <p className="text-sm text-[var(--muted)]">
                Sign in to your FinSight account
              </p>
            </div>
          </div>

          <div className="panel space-y-4 rounded-2xl p-6">
            {authError && (
              <p className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-400">
                {authError}
              </p>
            )}
            {message && (
              <p className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-400">
                {message}
              </p>
            )}

            {!configured ? (
              <div className="space-y-3 text-sm text-[var(--muted)]">
                <p>Sign-in is not available on this deployment yet.</p>
                <p>Contact your administrator if you believe this is a mistake.</p>
              </div>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => void signInWithGoogle()}
                  disabled={loading !== null}
                  className="btn-ghost flex w-full items-center justify-center gap-3 rounded-xl px-4 py-3 text-sm font-medium"
                >
                  {loading === "google" ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <GoogleIcon />
                  )}
                  Continue with Google
                </button>

                <div className="flex items-center gap-3">
                  <div className="h-px flex-1 bg-[var(--border)]" />
                  <span className="text-xs text-[var(--muted)]">or</span>
                  <div className="h-px flex-1 bg-[var(--border)]" />
                </div>

                <form onSubmit={(e) => void signInWithEmail(e)} className="space-y-3">
                  <label className="block text-xs font-medium text-[var(--muted)]">
                    Email sign-in link
                  </label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Mail
                        size={14}
                        className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]"
                      />
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@example.com"
                        required
                        className="input-field w-full py-2.5 pl-9 pr-3"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={loading !== null || !email.trim()}
                      className="btn-primary shrink-0 rounded-xl px-4 py-2.5 text-sm disabled:opacity-40"
                    >
                      {loading === "email" ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        "Send link"
                      )}
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>

          <p className="text-center text-xs text-[var(--muted)] lg:text-left">
            By continuing, you agree to keep your login credentials private.
          </p>
        </div>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm text-[var(--muted)]">
          Loading…
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
