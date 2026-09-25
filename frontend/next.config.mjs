import path from "path";
import { fileURLToPath } from "url";
import nextEnv from "@next/env";

const { loadEnvConfig } = nextEnv;
const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Monorepo: load repo-root .env when running locally from frontend/
loadEnvConfig(path.join(__dirname, ".."));

/**
 * Same-origin API proxy target (server-side only).
 * Browser calls /backend/* on the frontend host; Next rewrites to the real API.
 * This bypasses cross-origin browser blocks (Safari "Load failed") that hit when
 * the UI talks directly to a different Railway hostname.
 */
const apiProxyTarget = (
  process.env.API_PROXY_TARGET ||
  (process.env.NEXT_PUBLIC_API_URL?.startsWith("http")
    ? process.env.NEXT_PUBLIC_API_URL
    : "") ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // No standalone — Railway uses `next start` reliably without it.
  devIndicators: false,
  async redirects() {
    return [
      {
        source: "/favicon.ico",
        destination: "/favicon.svg",
        permanent: false,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${apiProxyTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;
