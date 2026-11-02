import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api/* is proxied to the Flask backend so the browser never hits CORS.
export default defineConfig({
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
