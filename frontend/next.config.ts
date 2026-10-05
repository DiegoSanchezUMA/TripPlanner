import { createVanillaExtractPlugin } from "@vanilla-extract/next-plugin";
import type { NextConfig } from "next";

// El soporte de Turbopack del plugin es experimental: se compila con Webpack
// (scripts dev y build con --webpack, D-018).
const withVanillaExtract = createVanillaExtractPlugin();

const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default withVanillaExtract(nextConfig);
