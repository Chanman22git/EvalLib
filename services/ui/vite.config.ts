import { copyFileSync, existsSync } from "node:fs";
import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vitest/config";

// GitHub Pages serves a project site under /<repo>/ and returns its own 404 for
// any path the SPA owns (e.g. /agents). Copying index.html to 404.html makes
// Pages serve the app for unknown paths so React Router can resolve them.
function spa404Fallback(): Plugin {
  return {
    name: "spa-404-fallback",
    apply: "build",
    closeBundle() {
      const dist = path.resolve(__dirname, "dist");
      const index = path.join(dist, "index.html");
      if (existsSync(index)) copyFileSync(index, path.join(dist, "404.html"));
    },
  };
}

export default defineConfig({
  // Project Pages are served from /<repo>/. Override with VITE_BASE for other hosts.
  base: process.env.VITE_BASE ?? "/",
  plugins: [react(), spa404Fallback()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    host: true,
  },
  preview: {
    port: 3000,
    host: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
