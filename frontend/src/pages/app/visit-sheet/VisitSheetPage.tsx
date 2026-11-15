import { Link } from "react-router";
import { getProfile, getVisitSheet } from "../../../api/app";
import type { VisitSheet } from "../../../api/appTypes";
import { useAppCopy } from "../../../api/AppDataProvider";
import { useAppRequest } from "../../../api/useAppRequest";
import { StatusBlock } from "../../../components/StatusBlock";
import { VISIT } from "../../../content/app/visit";
import { Seo, pageTitle } from "../../../layout/Seo";
import { ROUTES } from "../../../routes";
import { SheetPreview } from "./SheetPreview";
import { useVisitAutosave } from "./useVisitAutosave";
import { VisitSheetEditor } from "./VisitSheetEditor";
import { draftFrom } from "./visitDraft";
import styles from "./VisitSheet.module.css";

/** `/visit-sheet`: prepare and print a one-page doctor-visit sheet. */
export default function VisitSheetPage() {
  const sheet = useAppRequest((signal) => getVisitSheet(signal), []);
  const copy = useAppCopy();
  const profile = useAppRequest((signal) => getProfile(signal), []);

  if (sheet.handled) return null;
  if (sheet.status === "error" || copy.status === "error") {
    return (
      <>
        <PageMeta title={VISIT.sheetTitle} />
        <h1 data-app-heading tabIndex={-1} className={styles.h1}>
          {VISIT.sheetTitle}
        </h1>
        <StatusBlock
          status="error"
          what={VISIT.loadingWhat}
          onRetry={() => {
            sheet.retry();
            copy.refresh();
          }}
        />
      </>
    );
  }
  if (sheet.status !== "ready" || copy.status !== "ready") {
    return (
      <>
        <PageMeta title={VISIT.sheetTitle} />
        <h1 data-app-heading tabIndex={-1} className={styles.h1}>
          {VISIT.sheetTitle}
        </h1>
        <StatusBlock status="loading" what={VISIT.loadingWhat} onRetry={() => undefined} />
      </>
    );
  }
  const preparedBy = profile.status === "ready" ? profile.data.caregiverFirstName : null;
  return (
    <VisitSheetReady
      sheet={sheet.data}
      title={copy.data.visitSheet.title}
      subtitle={copy.data.visitSheet.subtitle}
      preparedBy={preparedBy}
    />
  );
}

function PageMeta({ title }: { title: string }) {
  return (
    <>
      <Seo title={pageTitle(title)} description={VISIT.sheetTitle} />
      <meta name="robots" content="noindex" />
    </>
  );
}

interface ReadyProps {
  sheet: VisitSheet;
  title: string;
  subtitle: string;
  preparedBy: string | null;
}

function VisitSheetReady({ sheet, title, subtitle, preparedBy }: ReadyProps) {
  const autosave = useVisitAutosave(draftFrom(sheet));
  const { status, flush } = autosave;
  const print = async (): Promise<void> => {
    await flush();
    window.print();
  };
  return (
    <div className={styles.page}>
      <PageMeta title={VISIT.sheetTitle} />
      <Link to={ROUTES.today} className={styles.back}>
        {VISIT.backToToday}
      </Link>
      <h1 data-app-heading tabIndex={-1} className={styles.h1}>
        {title}
      </h1>
      <p className={styles.hint}>{subtitle}</p>
      <div className={styles.status} role="status" aria-live="polite">
        {status.kind === "saving" && VISIT.saving}
        {status.kind === "saved" && VISIT.saved}
      </div>
      {status.kind === "error" && (
        <div className={styles.error} role="alert">
          <p>
            {VISIT.notSaved} {status.message}
          </p>
          <button type="button" className={styles.secondary} onClick={() => void flush()}>
            {VISIT.saveRetry}
          </button>
        </div>
      )}
      <VisitSheetEditor sheet={sheet} autosave={autosave} />
      <h2 className={styles.h2}>{VISIT.previewTitle}</h2>
      <SheetPreview draft={autosave.draft} footer={sheet.footer} preparedBy={preparedBy} />
      <p className={styles.hint}>{VISIT.printHint}</p>
      <button type="button" className={styles.primary} onClick={() => void print()}>
        {VISIT.printButton}
      </button>
    </div>
  );
}
