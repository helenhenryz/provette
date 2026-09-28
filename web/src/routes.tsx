import { Fragment, type ReactNode } from "react";
import { type RouteObject, useLocation } from "react-router-dom";
import { Shell } from "./components/Shell";
import { AboutPage } from "./pages/About";
import { CheckPage } from "./pages/Check";
import { CheckResultPage } from "./pages/CheckResult";
import { DocPage } from "./pages/Doc";
import { EpisodePage } from "./pages/Episode";
import { ErrorPage } from "./pages/ErrorPage";
import { GalleryPage } from "./pages/Gallery";
import { HomePage } from "./pages/Home";
import { HowPage } from "./pages/How";
import { KnowsPage } from "./pages/Knows";
import { NotFoundPage } from "./pages/NotFound";
import { PlanPage } from "./pages/Plan";
import { RuleFormPage } from "./pages/RuleForm";
import { RunResultPage } from "./pages/RunResult";

/* One route per page. A page composes components and fetches through lib/api.ts. */

/* A page of one record (a run, a plan, a check, an example) starts afresh when the record
   changes: History links from one run to another on the same route, and without a new key the
   page would keep the last run's analysis and replay under the new run's title. */
export function PerRecord({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  return <Fragment key={pathname}>{children}</Fragment>;
}

export function routes(): RouteObject[] {
  return [
    {
      path: "/",
      element: <Shell />,
      errorElement: <ErrorPage />,
      children: [
        { index: true, element: <HomePage /> },
        { path: "examples", element: <GalleryPage /> },
        {
          path: "plan/:id",
          element: (
            <PerRecord>
              <PlanPage />
            </PerRecord>
          ),
        },
        {
          path: "runs/:id",
          element: (
            <PerRecord>
              <RunResultPage />
            </PerRecord>
          ),
        },
        {
          path: "episodes/:set/:condition/:requestId",
          element: (
            <PerRecord>
              <EpisodePage />
            </PerRecord>
          ),
        },
        { path: "check", element: <CheckPage /> },
        {
          path: "check/:id",
          element: (
            <PerRecord>
              <CheckResultPage />
            </PerRecord>
          ),
        },
        { path: "methods", element: <HowPage /> },
        { path: "rules", element: <KnowsPage /> },
        { path: "rules/new", element: <RuleFormPage /> },
        { path: "docs/:name", element: <DocPage /> },
        { path: "about", element: <AboutPage /> },
        { path: "*", element: <NotFoundPage /> },
      ],
    },
  ];
}
