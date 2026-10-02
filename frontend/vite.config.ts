import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The dev server proxies /api to the backend, so one HTTPS tunnel to :5173 is enough
// for testing the Mini App inside Telegram.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: true,
    proxy: { "/api": "http://localhost:8000" },
  },
});
