import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Phase 7: dev server on Vite's default port 5173, matching backend's
// config.yaml `server.cors_origins` default. strictPort: fail loudly if 5173 is taken
// instead of silently drifting to 5174+ -- a silent drift breaks CORS in a confusing way
// (browser origin no longer matches the backend's allowlist) rather than an obvious
// "port in use" error at startup.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
  },
});
