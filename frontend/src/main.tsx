import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/figtree/wght.css"; // Figtree, SIL OFL 1.1, self-hosted by Vite
import "./styles/tokens.css";
import "./styles/global.css";
import { RouterProvider } from "react-router/dom";
import { createAppRouter } from "./router";

const root = document.getElementById("root");
if (root === null) throw new Error("Missing #root element");
createRoot(root).render(
  <StrictMode>
    <RouterProvider router={createAppRouter()} />
  </StrictMode>,
);
