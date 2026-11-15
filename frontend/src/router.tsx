import type { ComponentType } from "react";
import { createBrowserRouter, type RouteObject } from "react-router";
import { AppLayout } from "./layout/app/AppLayout";
import { FunnelLayout } from "./layout/funnel/FunnelLayout";
import { CardLayout } from "./pages/card/CardLayout";
import { GuideLayout } from "./pages/guide/GuideLayout";
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
      {
        path: ROUTES.fakeCheckout,
        ...page(() => import("./pages/funnel/FakeCheckoutPage")),
      },
    ],
  },
  {
    element: <AppLayout />,
    HydrateFallback: () => null,
    children: [
      { path: ROUTES.today, ...page(() => import("./pages/app/TodayPage")) },
      {
        path: ROUTES.todayPractice,
        ...page(() => import("./pages/app/today/PracticeRoundPage")),
      },
      {
        path: ROUTES.lesson,
        ...page(() => import("./pages/app/lesson/LessonPage")),
      },
      {
        path: ROUTES.appPlan,
        ...page(() => import("./pages/app/plan/PlanTabPage")),
      },
      {
        path: ROUTES.profile,
        ...page(() => import("./pages/app/profile/ProfilePage")),
      },
      {
        path: ROUTES.careCard,
        ...page(() => import("./pages/app/care-card/CareCardPage")),
      },
      {
        path: ROUTES.visitSheet,
        ...page(() => import("./pages/app/visit-sheet/VisitSheetPage")),
      },
      {
        path: ROUTES.skills,
        ...page(() => import("./pages/app/skills/SkillsPage")),
      },
      {
        path: ROUTES.settings,
        ...page(() => import("./pages/app/settings/SettingsPage")),
      },
      {
        path: ROUTES.settingsCancel,
        ...page(() => import("./pages/app/settings/CancelPage")),
      },
      {
        path: ROUTES.settingsGentleExit,
        ...page(() => import("./pages/app/settings/GentleExitPage")),
      },
    ],
  },
  {
    // The session is gone after the gentle exit, so /goodbye lives outside AppLayout.
    HydrateFallback: () => null,
    children: [
      {
        path: ROUTES.goodbye,
        ...page(() => import("./pages/app/settings/GoodbyePage")),
      },
    ],
  },
  {
    element: <CardLayout />,
    HydrateFallback: () => null,
    children: [
      { path: ROUTES.card, ...page(() => import("./pages/card/CardPage")) },
    ],
  },
  {
    // Public quick guides: no session, no gate.
    element: <GuideLayout />,
    HydrateFallback: () => null,
    children: [
      { path: ROUTES.guide, ...page(() => import("./pages/guide/GuidePage")) },
    ],
  },
];

export const createAppRouter = () => createBrowserRouter(routes);
