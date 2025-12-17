import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://backend:8000/:path*",
      },
      {
        source: "/media/:path*",
        destination: "http://backend:8000/media/:path*",
      },
      {
        source: "/docs",
        destination: "http://backend:8000/docs",
      },
      {
        source: "/openapi.json",
        destination: "http://backend:8000/openapi.json",
      },
    ];
  },
};

export default nextConfig;
