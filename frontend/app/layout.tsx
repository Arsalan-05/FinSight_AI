import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Sidebar from "@/components/Sidebar";
import { ToastProvider } from "@/contexts/ToastContext";
import { Providers } from "./providers";
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
      <body className="flex min-h-full bg-zinc-950 text-zinc-50 transition-colors duration-200">
        <Providers>
          <ToastProvider>
            <Sidebar />
            <main className="flex-1 md:ml-60 min-h-screen">{children}</main>
          </ToastProvider>
        </Providers>
      </body>
    </html>
  );
}
