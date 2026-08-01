import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Test-only: exercised by the wrapper browser job. It is never used by production builds.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: {
    host: "127.0.0.1",
    port: 4180,
    strictPort: true,
    proxy: { "/api": { target: "http://127.0.0.1:4181", changeOrigin: true } },
  },
});
