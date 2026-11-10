import type { NextConfig } from "next";
const config: NextConfig = {
  devIndicators: false,
  turbopack: { root: import.meta.dirname },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.WATT_API_ORIGIN ?? "http://127.0.0.1:8000"}/api/:path*` }];
  },
};
export default config;
