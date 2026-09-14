/** @type {import('next').NextConfig} */
const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/ingest", destination: `${API_BASE}/ingest` },
      { source: "/search", destination: `${API_BASE}/search` },
      { source: "/events/:path*", destination: `${API_BASE}/events/:path*` },
      { source: "/metrics", destination: `${API_BASE}/metrics` },
      { source: "/verify-chain", destination: `${API_BASE}/verify-chain` },
      { source: "/drift/:path*", destination: `${API_BASE}/drift/:path*` },
      { source: "/mapping/:path*", destination: `${API_BASE}/mapping/:path*` },
      { source: "/compliance/:path*", destination: `${API_BASE}/compliance/:path*` },
    ];
  },
};

module.exports = nextConfig;
