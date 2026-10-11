import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" makes the built site work at any address, including
// https://<user>.github.io/<repo>/ on GitHub Pages.
export default defineConfig({
  base: "./",
  plugins: [react()],
});
