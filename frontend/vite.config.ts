/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { apiProxy } from "./src/devProxy";

export default defineConfig({
  plugins: [react()],
  server: { port: 3000, proxy: { ...apiProxy } },
  build: { sourcemap: false },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
