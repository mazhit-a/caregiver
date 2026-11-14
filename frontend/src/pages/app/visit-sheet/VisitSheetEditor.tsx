import { useState } from "react";
import { APP_COMMON } from "../../../content/app/common";
import { VISIT, VISIT_LIMITS } from "../../../content/app/visit";
import type { VisitSheet } from "../../../api/appTypes";
import type { Autosave } from "./useVisitAutosave";
import { addBlock, appendNote, move, newKey } from "./visitDraft";
import styles from "./VisitSheet.module.css";

interface Props {
  sheet: VisitSheet;
  autosave: Autosave;
}

export function VisitSheetEditor({ sheet, autosave }: Props) {
  const { draft, edit, flush } = autosave;
  const [own, setOwn] = useState("");
  const [notesFull, setNotesFull] = useState(false);
  const chosen = new Set(draft.questions.map((q) => q.id).filter((id) => id !== null));
  const bank = sheet.bank.filter((b) => !chosen.has(b.id));
  const blockedTotal = addBlock(draft.questions, false) === "total";
  const blockedOwn = addBlock(draft.questions, true);
  const ownText = own.trim();

  const addBank = (id: string, text: string): void =>
    edit((d) => ({ ...d, questions: [...d.questions, { key: newKey(), id, text }] }));
  const addOwn = (): void => {
    if (ownText === "" || blockedOwn) return;
    edit((d) => ({ ...d, questions: [...d.questions, { key: newKey(), id: null, text: ownText }] }));
    setOwn("");
  };
  const addNote = (text: string): void => {
    const next = appendNote(draft.familyNotes, text);
    setNotesFull(next === null);
    if (next !== null) edit((d) => ({ ...d, familyNotes: next }));
  };
  const onBlur = (): void => void flush();

  return (
    <div className={styles.editor}>
      <div className={styles.row}>
        <label className={styles.field}>
          <span>{VISIT.doctorLabel}</span>
          <input
            type="text"
            value={draft.doctor}
            maxLength={VISIT_LIMITS.doctor}
            onChange={(e) => edit((d) => ({ ...d, doctor: e.target.value }))}
            onBlur={onBlur}
          />
        </label>
        <label className={styles.field}>
          <span>{VISIT.dateLabel}</span>
          <input
            type="date"
            value={draft.visitDate}
            onChange={(e) => edit((d) => ({ ...d, visitDate: e.target.value }))}
            onBlur={onBlur}
          />
        </label>
      </div>

      <section className={styles.card} aria-labelledby="visit-notes">
        <h2 id="visit-notes" className={styles.h2}>
          {VISIT.notesTitle}
        </h2>
        <p className={styles.hint}>{VISIT.notesHint}</p>
        <textarea
          aria-labelledby="visit-notes"
          rows={6}
          value={draft.familyNotes}
          maxLength={VISIT_LIMITS.familyNotes}
          onChange={(e) => {
            setNotesFull(false);
            edit((d) => ({ ...d, familyNotes: e.target.value }));
          }}
          onBlur={onBlur}
        />
        <p className={styles.counter}>
          {draft.familyNotes.length} / {VISIT_LIMITS.familyNotes}
        </p>
        {notesFull && <p role="alert">{VISIT.notesFull}</p>}
        {sheet.suggestedNotes.length > 0 && (
          <>
            <h3 className={styles.h3}>{VISIT.suggestedTitle}</h3>
            <p className={styles.hint}>{VISIT.suggestedHint}</p>
            <ul className={styles.list} aria-label={VISIT.suggestedTitle}>
              {sheet.suggestedNotes.map((note) => (
                <li key={note.id} className={styles.item}>
                  <span className={styles.itemText}>{note.text}</span>
                  <button
                    type="button"
                    className={styles.secondary}
                    aria-label={`${VISIT.addToNotes}: ${note.text}`}
                    onClick={() => addNote(note.text)}
                  >
                    {VISIT.addToNotes}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className={styles.card} aria-labelledby="visit-questions">
        <h2 id="visit-questions" className={styles.h2}>
          {VISIT.questionsTitle}
        </h2>
        {draft.questions.length === 0 ? (
          <p className={styles.hint}>{VISIT.questionsEmpty}</p>
        ) : (
          <ol className={styles.list} aria-label={VISIT.questionsTitle}>
            {draft.questions.map((q, i) => (
              <li key={q.key} className={styles.item}>
                <span className={styles.itemText}>{q.text}</span>
                <span className={styles.actions}>
                  <button
                    type="button"
                    className={styles.icon}
                    aria-label={`${VISIT.moveUp}: ${q.text}`}
                    disabled={i === 0}
                    onClick={() => edit((d) => ({ ...d, questions: move(d.questions, i, i - 1) }))}
                  >
                    <span aria-hidden="true">↑</span>
                  </button>
                  <button
                    type="button"
                    className={styles.icon}
                    aria-label={`${VISIT.moveDown}: ${q.text}`}
                    disabled={i === draft.questions.length - 1}
                    onClick={() => edit((d) => ({ ...d, questions: move(d.questions, i, i + 1) }))}
                  >
                    <span aria-hidden="true">↓</span>
                  </button>
                  <button
                    type="button"
                    className={styles.secondary}
                    aria-label={`${VISIT.remove}: ${q.text}`}
                    onClick={() =>
                      edit((d) => ({ ...d, questions: d.questions.filter((x) => x.key !== q.key) }))
                    }
                  >
                    {VISIT.remove}
                  </button>
                </span>
              </li>
            ))}
          </ol>
        )}
        {blockedTotal && <p className={styles.hint}>{VISIT.tooManyQuestions}</p>}

        <h3 className={styles.h3}>{VISIT.bankTitle}</h3>
        {bank.length === 0 ? (
          <p className={styles.hint}>{VISIT.bankEmpty}</p>
        ) : (
          <ul className={styles.list} aria-label={VISIT.bankTitle}>
            {bank.map((b) => (
              <li key={b.id} className={styles.item}>
                <span className={styles.itemText}>{b.text}</span>
                <button
                  type="button"
                  className={styles.secondary}
                  aria-label={`${VISIT.add}: ${b.text}`}
                  disabled={blockedTotal}
                  onClick={() => addBank(b.id, b.text)}
                >
                  {VISIT.add}
                </button>
              </li>
            ))}
          </ul>
        )}

        <h3 className={styles.h3}>{VISIT.ownTitle}</h3>
        <form
          className={styles.ownForm}
          onSubmit={(e) => {
            e.preventDefault();
            addOwn();
          }}
        >
          <label className={styles.field}>
            <span>{VISIT.ownLabel}</span>
            <input
              type="text"
              value={own}
              maxLength={VISIT_LIMITS.customQuestionLength}
              onChange={(e) => setOwn(e.target.value)}
            />
          </label>
          <button type="submit" className={styles.secondary} disabled={ownText === "" || blockedOwn !== null}>
            {VISIT.ownAdd}
          </button>
        </form>
        {blockedOwn === "custom" && <p className={styles.hint}>{VISIT.tooManyOwn}</p>}
      </section>
      <p className={styles.hint}>{APP_COMMON.privacyShort}</p>
    </div>
  );
}
