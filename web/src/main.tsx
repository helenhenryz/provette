import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import "./base.css";
import { routes } from "./routes";

/* The routes are in routes.tsx, one per page; the builder's pages are in the development
   build only. */
const router = createBrowserRouter(routes());

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
