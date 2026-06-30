import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";

export const metadata = {
  title: "Privacy",
};

export default function PrivacyPage() {
  return (
    <div className="page-container max-w-2xl gap-8">
      <PageHeader
        eyebrow="Trust"
        title="Privacy"
        subtitle="How FinSight handles your financial data."
      />

      <article className="panel space-y-6 rounded-2xl p-6 text-sm leading-relaxed text-[var(--muted)]">
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
            <li>Financial goals you set in the app</li>
          </ul>
        </section>

        <section>
          <h2 className="mb-2 text-base font-semibold text-[var(--foreground)]">Bank connections</h2>
          <p>
            When you connect a bank through our linking partner, FinSight receives read-only
            transaction data. We never store your online banking password.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-base font-semibold text-[var(--foreground)]">Export & deletion</h2>
          <p>
            You can download a CSV of all transactions anytime from{" "}
            <Link href="/settings" className="link-accent">
              Settings
            </Link>
            . To request full account deletion, contact support or sign out and disconnect linked banks.
          </p>
        </section>

        <section>
          <h2 className="mb-2 text-base font-semibold text-[var(--foreground)]">Security</h2>
          <p>
            Data is encrypted in transit (HTTPS). Production deployments use authenticated database
            access and row-level isolation per user.
          </p>
        </section>
      </article>

      <Link href="/settings" className="link-accent text-sm">
        ← Back to Settings
      </Link>
    </div>
  );
}
