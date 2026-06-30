import Link from "next/link";

import { Logo } from "@/components/brand/Logo";

export const metadata = {
  title: "Privacy",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[var(--background)] px-4 py-10">
      <div className="mesh-bg" aria-hidden />
      <div className="relative mx-auto max-w-2xl">
        <div className="mb-8">
          <Link href="/login">
            <Logo size={40} compact subtitle="" />
          </Link>
        </div>

        <article className="panel space-y-6 rounded-2xl p-6 text-sm leading-relaxed text-[var(--muted)]">
          <header>
            <h1 className="text-2xl font-semibold text-[var(--foreground)]">Privacy Policy</h1>
            <p className="mt-2">How FinSight handles your financial data.</p>
          </header>

          <section>
            <h2 className="mb-2 text-base font-semibold text-[var(--foreground)]">Your data belongs to you</h2>
            <p>
              FinSight stores your transactions and chat history so the advisor can answer questions
              about your real spending. We do not sell your data. Access is limited to your signed-in
              account.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-[var(--foreground)]">What we collect</h2>
            <ul className="list-inside list-disc space-y-1">
              <li>Profile information from your sign-in provider (name, email)</li>
              <li>Bank account labels and transaction data you import or link</li>
              <li>Chat messages with the finance advisor</li>
              <li>Financial goals and budget preferences you set in the app</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-[var(--foreground)]">Bank connections</h2>
            <p>
              When you connect a bank through our linking partner (Plaid), FinSight receives read-only
              transaction data. We never store your online banking password. You can disconnect banks
              anytime in Settings.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-[var(--foreground)]">Export & deletion</h2>
            <p>
              Signed-in users can download a full data export or permanently delete their account from
              Settings. Deletion removes accounts, transactions, chat history, and bank connections.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-base font-semibold text-[var(--foreground)]">Security</h2>
            <p>
              Data is encrypted in transit (HTTPS). Plaid access tokens can be encrypted at rest when
              configured. Production deployments use authenticated database access and per-user data
              isolation.
            </p>
          </section>
        </article>

        <div className="mt-6 flex gap-4">
          <Link href="/login" className="link-accent text-sm">Sign in</Link>
          <Link href="/" className="link-accent text-sm">Open app</Link>
        </div>
      </div>
    </div>
  );
}
