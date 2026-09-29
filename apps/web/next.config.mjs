const demo = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

/** @type {import('next').NextConfig} */
const nextConfig = demo
  ? { output: "export", distDir: ".next-demo", basePath, images: { unoptimized: true }, trailingSlash: true }
  : {};

export default nextConfig;
