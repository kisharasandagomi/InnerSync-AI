import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Temporary: allows the ngrok tunnel's Host header through during Phase 8
    // testing. Revert (remove allowedHosts) once the tunnel is torn down.
    allowedHosts: ['.ngrok-free.app', '.ngrok-free.dev', '.ngrok.io', '.ngrok.app'],
    // The browser talks only to this origin; Vite forwards /api to the FastAPI
    // backend, so the API stays same-origin in development.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
