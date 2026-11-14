import type { ComponentType } from "react";
import { createBrowserRouter, type RouteObject } from "react-router";
import { FunnelLayout } from "./layout/funnel/FunnelLayout";
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
      {
        path: ROUTES.practice,
        ...page(() => import("./pages/practice/PracticePage")),
      },
      {
        path: ROUTES.course,
        ...page(() => import("./pages/course/CoursePage")),
      },
      { path: ROUTES.tools, ...page(() => import("./pages/tools/ToolsPage")) },
      {
        path: ROUTES.pricing,
        ...page(() => import("./pages/pricing/PricingPage")),
      },
      { path: "*", ...page(() => import("./pages/NotFoundPage")) },
    ],
  },
  {
    element: <FunnelLayout />,
    HydrateFallback: () => null,
    children: [
      { path: ROUTES.quiz, ...page(() => import("./pages/quiz/QuizPage")) },
      // Static `building` outranks `:questionId`. F5 replaces src/pages/quiz/QuizStepPage.tsx.
      {
        path: ROUTES.quizBuilding,
        ...page(() => import("./pages/funnel/BuildingPage")),
      },
      {
        path: `${ROUTES.quiz}/:questionId`,
        ...page(() => import("./pages/quiz/QuizStepPage")),
      },
      { path: ROUTES.plan, ...page(() => import("./pages/funnel/PlanPage")) },
      { path: ROUTES.gift, ...page(() => import("./pages/funnel/GiftPage")) },
      {
        path: ROUTES.paywall,
        ...page(() => import("./pages/funnel/PaywallPage")),
      },
      {
        path: ROUTES.checkoutReturn,
        ...page(() => import("./pages/funnel/CheckoutReturnPage")),
      },
      { path: ROUTES.today, ...page(() => import("./pages/app/TodayPage")) },
    ],
  },
];

export const createAppRouter = () => createBrowserRouter(routes);
