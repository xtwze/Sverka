import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api/agent": "http://localhost:8081",
      "/api": "http://localhost:8080",
    },
  },
});
