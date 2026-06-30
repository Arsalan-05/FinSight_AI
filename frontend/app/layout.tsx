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
    default: "FinSight — Personal Finance Intelligence",
    template: "%s · FinSight",
  },
  description:
    "Production-grade personal finance intelligence — transaction RAG, live market data, and a grounded finance agent.",
  applicationName: "FinSight AI",
  robots: { index: false, follow: false },
  openGraph: {
    title: "FinSight AI",
    description: "Personal finance intelligence with grounded AI and live market tools.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <Script id="theme-init" strategy="beforeInteractive">
          {`(function(){try{var t=localStorage.getItem("finsight-theme");document.documentElement.setAttribute("data-theme",t==="light"?"light":"dark")}catch(e){document.documentElement.setAttribute("data-theme","dark")}})()`}
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
