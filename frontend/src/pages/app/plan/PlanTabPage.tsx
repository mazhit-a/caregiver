import { useEffect, useState } from "react";
import { getPlan, getToday } from "../../../api/app";
import { getPlanPreview } from "../../../api/funnel";
import { useAppCopy } from "../../../api/AppDataProvider";
import { useAppRequest } from "../../../api/useAppRequest";
import { StatusBlock } from "../../../components/StatusBlock";
import { PLAN_TEXT } from "../../../content/app/plan";
import { Seo, pageTitle } from "../../../layout/Seo";
import { ModulesGrid } from "./ModulesGrid";
import { PathView } from "./PathView";
import { QuickGuides } from "./QuickGuides";
import { buildModules, currentLessonId } from "./planModel";
import styles from "./plan.module.css";

type View = "path" | "all";

export default function PlanTabPage() {
  const request = useAppRequest(async (signal) => {
    const [plan, preview, today] = await Promise.all([
      getPlan(signal),
      getPlanPreview(signal),
      getToday(signal),
    ]);
    return { plan, preview, today };
  }, []);
  const appCopy = useAppCopy();
  const [view, setView] = useState<View>("path");
  const [focusModule, setFocusModule] = useState<string | null>(null);

  useEffect(() => {
    if (view !== "path" || !focusModule) return;
    const el = document.getElementById(`module-${focusModule}`);
    el?.scrollIntoView?.({ block: "start" });
    el?.focus({ preventScroll: true });
    setFocusModule(null);
  }, [view, focusModule]);

  const seo = <Seo title={pageTitle("Plan")} description="Your course, one topic at a time." />;
  if (request.handled) return null;
  if (request.status === "loading" || (request.status === "ready" && appCopy.status !== "ready")) {
    return (
      <>
        {seo}
        <meta name="robots" content="noindex" />
        <h1 data-app-heading tabIndex={-1}>{PLAN_TEXT.loadingHeading}</h1>
        <StatusBlock status="loading" what={PLAN_TEXT.what} onRetry={request.retry} />
      </>
    );
  }
  if (request.status === "error") {
    return (
      <>
        {seo}
        <meta name="robots" content="noindex" />
        <h1 data-app-heading tabIndex={-1}>{PLAN_TEXT.loadingHeading}</h1>
        <StatusBlock status="error" what={PLAN_TEXT.what} onRetry={request.retry} />
      </>
    );
  }

  if (appCopy.status !== "ready") return null;
  const copy = appCopy.data;
  const { plan, preview, today } = request.data;
  const modules = buildModules(plan, preview);
  const currentId = currentLessonId(plan, modules);
  const { done, total, text } = today.readiness;

  return (
    <>
      <Seo title={pageTitle(copy.plan.title)} description={copy.plan.subtitle} />
      <meta name="robots" content="noindex" />
      <header className={styles.header}>
        <h1 data-app-heading tabIndex={-1} className={styles.h1}>
          {copy.plan.title}
        </h1>
        <p className={styles.subtitle}>{copy.plan.subtitle}</p>
        <div
          className={styles.bar}
          role="progressbar"
          aria-label={PLAN_TEXT.progressLabel}
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={done}
          aria-valuetext={text}
        >
          <span style={{ width: total ? `${(done / total) * 100}%` : "0%" }} />
        </div>
        <p className={styles.progressText}>{text}</p>
        <fieldset className={styles.toggle}>
          <legend className={styles.srOnly}>{PLAN_TEXT.viewLegend}</legend>
          {(["path", "all"] as const).map((v) => (
            <label key={v} className={styles.toggleOption}>
              <input
                type="radio"
                name="plan-view"
                value={v}
                checked={view === v}
                onChange={() => setView(v)}
              />
              <span>{v === "path" ? PLAN_TEXT.viewPath : PLAN_TEXT.viewAll}</span>
            </label>
          ))}
        </fieldset>
      </header>
      {view === "path" ? (
        <PathView modules={modules} currentId={currentId} />
      ) : (
        <ModulesGrid
          modules={modules}
          onShowInPath={(id) => {
            setView("path");
            setFocusModule(id);
          }}
        />
      )}
      <QuickGuides
        title={copy.plan.quickGuidesTitle}
        caption={copy.plan.quickGuidesCaption}
        guides={preview.quickGuides}
      />
    </>
  );
}
