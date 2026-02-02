import path from "node:path";
import { config } from "dotenv";
import type { NextConfig } from "next";

// Load root .env so director-chat can use vars from video_explainer/.env.
// director-chat/.env.local still overrides for app-specific values.
config({ path: path.resolve(__dirname, "..", ".env") });

const nextConfig: NextConfig = {
  cacheComponents: true,
  images: {
    remotePatterns: [
      {
        hostname: "avatar.vercel.sh",
      },
      {
        protocol: "https",
        //https://nextjs.org/docs/messages/next-image-unconfigured-host
        hostname: "*.public.blob.vercel-storage.com",
      },
    ],
  },
};

export default nextConfig;
