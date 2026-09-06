import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // next/image defaults to the Vercel optimizer, which does not exist here.
  // Cloudflare Images or a custom loader replaces it when real images arrive.
  images: { unoptimized: true },
};

export default nextConfig;

// Gives `next dev` access to Cloudflare bindings, so local behaviour matches
// the deployed Worker.
import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";
initOpenNextCloudflareForDev();
