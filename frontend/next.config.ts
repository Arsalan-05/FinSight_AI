import type { NextConfig } from "next";
import path from "path";
import { loadEnvConfig } from "@next/env";

// Monorepo: load repo-root .env when running `npm run dev` from frontend/
loadEnvConfig(path.join(__dirname, ".."));

const nextConfig: NextConfig = {
  // Keep standalone for Docker; Railway Nixpacks uses `next start`.
  output: "standalone",
  // Ensure traced files resolve correctly when building in CI/monorepo layouts.
  outputFileTracingRoot: path.join(__dirname),
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
