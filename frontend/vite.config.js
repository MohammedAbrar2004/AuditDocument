import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Phase 7: dev server on Vite's default port 5173, matching backend's
// config.yaml `server.cors_origins` default.
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
    },
});
