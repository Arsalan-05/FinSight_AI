import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";
import AuthLayout from "@/components/shell/AuthLayout";
import { ToastProvider } from "@/contexts/ToastContext";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "FinSight — Personal Finance",
    template: "%s · FinSight",
  },
  description:
    "Understand your money — spending insights, smart search, and a personal finance advisor grounded in your real transactions.",
  applicationName: "FinSight",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [{ url: "/favicon.svg", type: "image/svg+xml" }],
    apple: [{ url: "/apple-icon.svg", type: "image/svg+xml" }],
    shortcut: "/favicon.svg",
  },
  robots: { index: false, follow: false },
  openGraph: {
    title: "FinSight — Personal Finance",
    description: "Personal finance intelligence for Canadians.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      data-theme="light"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <Script id="theme-init" strategy="beforeInteractive">
          {`(function(){try{var t=localStorage.getItem("finsight-theme");document.documentElement.setAttribute("data-theme",t==="dark"?"dark":"light")}catch(e){document.documentElement.setAttribute("data-theme","light")}})()`}
        </Script>
      </head>
      <body className="min-h-full antialiased">
        <ToastProvider>
          <AuthLayout>{children}</AuthLayout>
        </ToastProvider>
      </body>
    </html>
  );
}
