import type { NextConfig } from "next";
import path from "path";
import { loadEnvConfig } from "@next/env";

// Monorepo: load repo-root .env when running `npm run dev` from frontend/
loadEnvConfig(path.join(__dirname, ".."));

const nextConfig: NextConfig = {
  // Do NOT use output:"standalone" — Next 16 breaks `next start` with it on Railway.
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
