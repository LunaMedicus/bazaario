import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_PORT = process.env.BAZAARIO_API_PORT || "5050";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${API_PORT}`,
        changeOrigin: true,
      },
      // Same-origin path to the public Google Translate endpoint so browser
      // CORS rules never block on-demand content translation.
      "/mt": {
        target: "https://translate.googleapis.com",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/mt/, ""),
      },
    },
  },
});
