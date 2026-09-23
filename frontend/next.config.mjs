import path from "path";
import { fileURLToPath } from "url";
import { loadEnvConfig } from "@next/env";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Monorepo: load repo-root .env when running locally from frontend/
loadEnvConfig(path.join(__dirname, ".."));

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
};

export default nextConfig;
