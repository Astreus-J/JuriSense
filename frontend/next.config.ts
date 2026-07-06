import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Build standalone: gera server.js com apenas as dependências necessárias,
  // dispensando node_modules completo na imagem Docker
  output: "standalone",
};

export default nextConfig;
