// this_file: review/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({ plugins: [react()], build: { outDir: "../src/vexy_localizzy/review/web", emptyOutDir: true }, server: { proxy: { "/api": "http://127.0.0.1:8765" } } });
