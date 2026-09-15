/** @type {import('next').NextConfig} */
const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    // One prefix for the whole API, so console routes like /events never collide with API paths.
    return [{ source: "/api/:path*", destination: `${API_BASE}/:path*` }];
  },
};

module.exports = nextConfig;
