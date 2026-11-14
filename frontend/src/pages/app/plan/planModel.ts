import type { CoursePlan } from "../../../api/appTypes";
import type { PlanPreview } from "../../../api/funnelTypes";

type PlanLesson = CoursePlan["modules"][number]["lessons"][number];

export interface ModuleView {
  id: string;
  title: string;
  reason: string;
  /** Preview status: current, next, later (anything else is shown as "Up next"). */
  status: string;
  inFirst30Days: boolean;
  lessons: PlanLesson[];
  doneCount: number;
}

const isOpen = (l: PlanLesson): boolean => l.status === "available" || l.status === "in_progress";

/** Display arithmetic only: the server decides order, reasons and every lesson state. */
export function buildModules(plan: CoursePlan, preview: PlanPreview): ModuleView[] {
  const byId = new Map(preview.modules.map((m) => [m.id, m]));
  return plan.modules.map((m) => {
    const extra = byId.get(m.id);
    return {
      id: m.id,
      title: m.title,
      reason: m.reason,
      status: extra?.status ?? "next",
      inFirst30Days: extra?.inFirst30Days ?? false,
      lessons: m.lessons,
      doneCount: m.lessons.filter((l) => l.status === "done").length,
    };
  });
}

/** The lesson that gets the halo: the server's hero when it is open, else the first open one. */
export function currentLessonId(plan: CoursePlan, modules: ModuleView[]): string | null {
  const all = modules.flatMap((m) => m.lessons);
  const hero = all.find((l) => l.id === plan.heroLessonId);
  if (hero && isOpen(hero)) return hero.id;
  return all.find(isOpen)?.id ?? null;
}

export const firstOpenLesson = (m: ModuleView): PlanLesson | undefined => m.lessons.find(isOpen);
