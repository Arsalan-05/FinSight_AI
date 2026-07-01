"use client";

import { usePathname } from "next/navigation";

import AppShell from "@/components/shell/AppShell";
import { ChatStreamProvider } from "@/contexts/ChatStreamContext";

const PUBLIC_PREFIXES = ["/login", "/auth/", "/privacy"];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublic = PUBLIC_PREFIXES.some((p) => pathname.startsWith(p));

  if (isPublic) {
    return <>{children}</>;
  }

  return (
    <ChatStreamProvider>
      <AppShell>{children}</AppShell>
    </ChatStreamProvider>
  );
}
