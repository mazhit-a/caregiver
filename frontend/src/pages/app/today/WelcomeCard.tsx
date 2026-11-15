import { useRef, useState } from "react";
import { getProfile, putProfile } from "../../../api/app";
import { useAppCopy } from "../../../api/AppDataProvider";
import { useAppAction, useAppRequest } from "../../../api/useAppRequest";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import { WELCOME } from "../../../content/app/checkin";
import { useTodayRefresh } from "./refresh";
import styles from "./welcome.module.css";

/**
 * First-run card: shown only while `GET /profile` has `updatedAt: null`. Continue saves a first name,
 * Skip saves an empty profile so the card does not return. A failed load hides it; it never blocks Today.
 */
export function WelcomeCard() {
  const profile = useAppRequest((signal) => getProfile(signal), []);
  const copy = useAppCopy();
  const runAction = useAppAction();
  const refreshToday = useTodayRefresh();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [closed, setClosed] = useState(false);
  const sending = useRef(false);

  if (closed || profile.status !== "ready" || profile.data.updatedAt !== null) return null;
  if (copy.status !== "ready") return null;
  const welcome = copy.data.welcome;

  async function save(displayName: string | null) {
    if (sending.current) return;
    sending.current = true;
    setBusy(true);
    setError(null);
    const res = await runAction(() => putProfile(displayName ? { displayName } : {}));
    sending.current = false;
    setBusy(false);
    if (!res.ok) {
      if (!res.handled) setError(APP_ERROR_MESSAGES[res.failure.kind]);
      return;
    }
    setClosed(true);
    copy.refresh();
    refreshToday();
  }

  return (
    <section className={styles.card} aria-labelledby="welcome-title">
      <h2 id="welcome-title" className={styles.title}>
        {welcome.title}
      </h2>
      <p className={styles.body}>{welcome.body}</p>
      <label className={styles.label}>
        {welcome.nameLabel}
        <input
          className={styles.input}
          type="text"
          autoComplete="off"
          maxLength={WELCOME.nameMax}
          value={name}
          disabled={busy}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <p className={styles.privacy}>{WELCOME.privacy}</p>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      <div className={styles.actions}>
        <button type="button" className={styles.primary} disabled={busy} onClick={() => void save(name.trim() || null)}>
          {busy ? WELCOME.saving : WELCOME.continue}
        </button>
        <button type="button" className={styles.secondary} disabled={busy} onClick={() => void save(null)}>
          {WELCOME.skip}
        </button>
      </div>
    </section>
  );
}
