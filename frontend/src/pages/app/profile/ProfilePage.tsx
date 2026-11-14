import { useState } from "react";
import { Link } from "react-router";
import { deletePhrase, getProfile, getVisitSheet, listPhrases, putProfile } from "../../../api/app";
import type { Profile, ProfileBody } from "../../../api/appTypes";
import { ApiError } from "../../../api/client";
import { useAppCopy } from "../../../api/AppDataProvider";
import { useAppAction, useAppRequest } from "../../../api/useAppRequest";
import ollieAvatar from "../../../assets/ollie-avatar.png";
import { StatusBlock } from "../../../components/StatusBlock";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import { PROFILE_TEXT } from "../../../content/app/profile";
import { formatDate } from "../../../format/date";
import { Seo, pageTitle } from "../../../layout/Seo";
import { ROUTES } from "../../../routes";
import { PhraseCards } from "./PhraseCards";
import { ProfileForm, type SaveOutcome } from "./ProfileForm";
import styles from "./profile.module.css";

function ChipCard({ title, items }: { title: string; items: string[] }) {
  return (
    <div className={styles.card}>
      <h3>{title}</h3>
      {items.length === 0 ? (
        <p className={styles.muted}>{PROFILE_TEXT.emptyChips}</p>
      ) : (
        <ul className={styles.chips}>
          {items.map((item, i) => (
            <li key={`${item}-${i}`} className={styles.chip}>
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function ProfilePage() {
  const act = useAppAction();
  const copy = useAppCopy();
  const profile = useAppRequest(getProfile, []);
  const phrases = useAppRequest(listPhrases, []);
  const visit = useAppRequest(getVisitSheet, []);
  const [saved, setSaved] = useState<Profile | null>(null);
  const [editing, setEditing] = useState(false);

  if (profile.handled || phrases.handled) return null;
  if (copy.status === "error" || profile.status === "error") {
    return (
      <StatusBlock
        status="error"
        what={PROFILE_TEXT.loadingWhat}
        onRetry={() => {
          copy.refresh();
          profile.retry();
        }}
      />
    );
  }
  if (copy.status === "loading" || profile.status === "loading") {
    return <StatusBlock status="loading" what={PROFILE_TEXT.loadingWhat} onRetry={() => undefined} />;
  }

  const text = copy.data.profile;
  const current = saved ?? profile.data;

  async function save(body: ProfileBody): Promise<SaveOutcome> {
    let message: string | null = null;
    const result = await act(async () => {
      try {
        return await putProfile(body);
      } catch (error) {
        if (error instanceof ApiError && error.code === "invalid_profile") message = error.message;
        throw error;
      }
    });
    if (!result.ok) {
      if (result.handled) return { ok: true };
      return { ok: false, message: message ?? APP_ERROR_MESSAGES[result.failure.kind] };
    }
    setSaved(result.data);
    setEditing(false);
    copy.refresh(); // the names in the page titles come from the server; the shell and this page update silently
    return { ok: true };
  }

  async function remove(id: string): Promise<boolean> {
    const result = await act(() => deletePhrase(id));
    if (result.ok) phrases.retry();
    return result.ok || result.handled;
  }

  const initial = (current.displayName ?? text.title).trim().charAt(0).toUpperCase();
  const visitData = visit.status === "ready" ? visit.data : null;

  return (
    <div className={styles.page}>
      <Seo title={pageTitle(text.title)} description={text.privacyNote} />
      <meta name="robots" content="noindex" />
      <header className={styles.header}>
        <div className={styles.avatar} aria-hidden="true">
          {current.displayName ? initial : <img src={ollieAvatar} alt="" />}
        </div>
        <div className={styles.headerText}>
          <h1 data-app-heading tabIndex={-1}>
            {text.title}
          </h1>
          <p className={styles.note}>{text.privacyNote}</p>
        </div>
        {!editing && (
          <button type="button" className={styles.btn} onClick={() => setEditing(true)}>
            {PROFILE_TEXT.edit}
          </button>
        )}
      </header>

      {editing ? (
        <ProfileForm profile={current} copy={text} onSave={save} onCancel={() => setEditing(false)} />
      ) : (
        <>
          <section className={styles.section} aria-labelledby="works-title">
            <h2 id="works-title">{text.worksTitle}</h2>
            {phrases.status === "error" ? (
              <StatusBlock status="error" what="saved phrases" onRetry={phrases.retry}>
                {null}
              </StatusBlock>
            ) : phrases.status === "loading" ? (
              <StatusBlock status="loading" what="saved phrases" onRetry={phrases.retry} />
            ) : (
              <PhraseCards phrases={phrases.data.phrases} emptyText={text.emptyPhrases} onDelete={remove} />
            )}
          </section>

          <section className={styles.section} aria-labelledby="about-title">
            <h2 id="about-title">{text.aboutTitle}</h2>
            <ChipCard title={text.enjoysTitle} items={current.enjoys} />
            <ChipCard title={text.calmsTitle} items={current.calms} />
            <ChipCard title={text.avoidTitle} items={current.avoid} />
            <div className={styles.card}>
              <h3>{text.rhythmTitle}</h3>
              <p className={current.rhythm ? undefined : styles.muted}>
                {current.rhythm || PROFILE_TEXT.emptyRhythm}
              </p>
            </div>
            <div className={styles.card}>
              <h3>{text.contactsTitle}</h3>
              {current.contacts.length === 0 ? (
                <p className={styles.muted}>{PROFILE_TEXT.emptyContacts}</p>
              ) : (
                <ul className={styles.contacts}>
                  {current.contacts.map((c, i) => (
                    <li key={`${c.name}-${i}`}>
                      {c.name}
                      {c.role ? `, ${c.role}` : ""}: <a href={`tel:${c.phone.replace(/[^+\d]/g, "")}`}>{c.phone}</a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <section className={styles.card} aria-labelledby="card-title">
            <h3 id="card-title">{copy.data.careCard.title}</h3>
            <p>{copy.data.careCard.purpose}</p>
            <p style={{ marginTop: "var(--space-3)" }}>
              <Link className={styles.btn} to={ROUTES.careCard}>
                {PROFILE_TEXT.careCardOpen}
              </Link>
            </p>
          </section>

          {visitData && (
            <section className={styles.card} aria-labelledby="visit-title">
              <h3 id="visit-title">{PROFILE_TEXT.visitTitle}</h3>
              <p className={visitData.visitDate ? undefined : styles.muted}>
                {visitData.visitDate
                  ? `${formatDate(visitData.visitDate, { year: true })}. ${
                      visitData.questions.length === 0
                        ? PROFILE_TEXT.visitNoQuestions
                        : visitData.questions.length === 1
                          ? PROFILE_TEXT.visitQuestionsOne
                          : PROFILE_TEXT.visitQuestionsMany(visitData.questions.length)
                    }`
                  : PROFILE_TEXT.visitEmpty}
              </p>
              <p style={{ marginTop: "var(--space-3)" }}>
                <Link className={styles.btn} to={ROUTES.visitSheet}>
                  {PROFILE_TEXT.visitOpen}
                </Link>
              </p>
            </section>
          )}
        </>
      )}
    </div>
  );
}
