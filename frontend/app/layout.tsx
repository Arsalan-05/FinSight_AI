import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";
import Sidebar from "@/components/Sidebar";
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
  title: "FinSight AI — Personal Finance Agent",
  description: "AI-powered personal finance intelligence. Powered by Claude and Voyage AI.",
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
      <body className="flex min-h-full bg-zinc-950 text-zinc-50 transition-colors duration-200">
        <ToastProvider>
          <Sidebar />
          <main className="flex-1 md:ml-60 min-h-screen">{children}</main>
        </ToastProvider>
      </body>
    </html>
  );
}
