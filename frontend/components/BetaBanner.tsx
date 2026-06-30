"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";

export function BetaBanner() {
  const [inviteOnly, setInviteOnly] = useState(false);

  useEffect(() => {
    api.capabilities().then((c) => {
      const beta = c.beta as { invite_only?: boolean } | undefined;
      setInviteOnly(Boolean(beta?.invite_only));
    }).catch(() => setInviteOnly(false));
  }, []);

  if (!inviteOnly) return null;

  return (
    <div className="border-b border-amber-500/25 bg-amber-500/10 px-4 py-2 text-center text-xs text-amber-200">
      FinSight invite-only beta — you have early access. Feedback welcome in Settings.
    </div>
  );
}
