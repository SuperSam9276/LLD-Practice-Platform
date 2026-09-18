import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api -> FastAPI on :8000.
// Reason: avoids adding CORS middleware to the backend just for local dev.
// In production the same origin would serve both, so no CORS story is needed at all.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
