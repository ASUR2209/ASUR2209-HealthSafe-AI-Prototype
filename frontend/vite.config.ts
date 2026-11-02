import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api/* is proxied to the Flask backend so the browser never hits CORS.
// BASE_PATH is set by the GitHub Pages workflow, which serves the app from /<repo>/.
export default defineConfig({
  base: process.env.BASE_PATH ?? "/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.HEALTHSAFE_API ?? "http://127.0.0.1:5000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
