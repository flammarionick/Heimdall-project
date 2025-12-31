// vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "localhost",
    port: 5173,
    proxy: {
      // API ONLY (do NOT proxy /admin frontend pages)
      "/auth/api": {
        target: "http://localhost:5002",
        changeOrigin: true,
      },
      "/admin/api": {
        target: "http://localhost:5002",
        changeOrigin: true,
      },
      "/api": {
        target: "http://localhost:5002",
        changeOrigin: true,
      },
      "/socket.io": {
        target: "http://localhost:5002",
        ws: true,
        changeOrigin: true,
      },
      "/static": {
        target: "http://localhost:5002",
        changeOrigin: true,
      },
    },
  },
});