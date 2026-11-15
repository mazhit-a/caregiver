import { formatDate } from "../../../format/date";
import { VISIT } from "../../../content/app/visit";
import type { Draft } from "./visitDraft";
import styles from "./VisitSheet.module.css";

interface Props {
  draft: Draft;
  footer: string;
  preparedBy: string | null;
}

/** What gets printed: one Letter page, black and white. Everything comes from the draft and the API. */
export function SheetPreview({ draft, footer, preparedBy }: Props) {
  const doctor = draft.doctor.trim();
  return (
    <section className={styles.sheet} aria-label={VISIT.previewTitle} data-testid="visit-sheet-print">
      <h2 className={styles.sheetTitle}>{VISIT.sheetTitle}</h2>
      {preparedBy && (
        <p className={styles.sheetMeta}>
          {VISIT.preparedBy} {preparedBy}
        </p>
      )}
      <dl className={styles.sheetFacts}>
        <div>
          <dt>{VISIT.sheetDoctor}</dt>
          <dd>{doctor || " "}</dd>
        </div>
        <div>
          <dt>{VISIT.sheetDate}</dt>
          <dd>{draft.visitDate ? formatDate(draft.visitDate, { year: true }) : " "}</dd>
        </div>
      </dl>
      <h3 className={styles.sheetHeading}>{VISIT.sheetNotes}</h3>
      <p className={styles.sheetNotes}>{draft.familyNotes || VISIT.sheetEmpty}</p>
      <h3 className={styles.sheetHeading}>{VISIT.sheetQuestions}</h3>
      {draft.questions.length === 0 ? (
        <p className={styles.sheetNotes}>{VISIT.sheetEmpty}</p>
      ) : (
        <ol className={styles.sheetQuestions} aria-label={VISIT.sheetQuestions}>
          {draft.questions.map((q) => (
            <li key={q.key}>{q.text}</li>
          ))}
        </ol>
      )}
      <h3 className={styles.sheetHeading}>{VISIT.sheetAnswers}</h3>
      <div className={styles.answerLines} aria-hidden="true">
        <span />
        <span />
        <span />
        <span />
      </div>
      <p className={styles.sheetFooter}>{footer}</p>
    </section>
  );
}
