// Dev server proxy table: the browser talks to /api on the same origin; Vite forwards to the backend.
export const apiProxy = {
  "/api": { target: "http://localhost:8000", changeOrigin: false },
} as const;
