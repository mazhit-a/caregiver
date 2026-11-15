import { useAppCopy } from "../../../../api/AppDataProvider";
import type { LessonCopy } from "../../../../api/appTypes";

/** The lesson wording block of `GET /app-copy`, or null until it has loaded. */
export function useLessonCopy(): LessonCopy | null {
  const copy = useAppCopy();
  return copy.status === "ready" ? copy.data.lesson : null;
}
