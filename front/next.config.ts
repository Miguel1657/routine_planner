import type { NextConfig } from "next";

// Internal address of the FastAPI service. Rewrites are resolved at build time,
// so in Docker this comes from the BACKEND_URL build arg (see front/Dockerfile).
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8001";

const nextConfig: NextConfig = {
  output: "standalone",
  // The browser only talks to this server; /api/* is proxied to the backend.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
  // LLM generation can take minutes; the default proxy timeout is much shorter.
  experimental: { proxyTimeout: 300_000 },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
