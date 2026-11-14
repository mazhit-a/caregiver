import type { ComponentType } from "react";
import { createBrowserRouter, type RouteObject } from "react-router";
import { RootLayout } from "./layout/RootLayout";
import { ROUTES } from "./routes";

const page = (load: () => Promise<{ default: ComponentType }>) => ({
  lazy: async () => ({ Component: (await load()).default }),
});

export const routes: RouteObject[] = [
  {
    element: <RootLayout />,
    HydrateFallback: () => null,
    children: [
      { path: ROUTES.home, ...page(() => import("./pages/home/HomePage")) },
      { path: ROUTES.how, ...page(() => import("./pages/how/HowPage")) },
      { path: ROUTES.practice, ...page(() => import("./pages/practice/PracticePage")) },
      { path: ROUTES.course, ...page(() => import("./pages/course/CoursePage")) },
      { path: ROUTES.tools, ...page(() => import("./pages/tools/ToolsPage")) },
      { path: ROUTES.pricing, ...page(() => import("./pages/pricing/PricingPage")) },
      { path: ROUTES.quiz, ...page(() => import("./pages/quiz/QuizPage")) },
      { path: "*", ...page(() => import("./pages/NotFoundPage")) },
    ],
  },
];

export const createAppRouter = () => createBrowserRouter(routes);
