import { useState, type FormEvent } from "react";
import type { AppCopy, Profile, ProfileBody } from "../../../api/appTypes";
import { PHONE_PATTERN, PROFILE_LIMITS, PROFILE_TEXT } from "../../../content/app/profile";
import { ChipEditor } from "./ChipEditor";
import styles from "./profile.module.css";

type ContactDraft = { name: string; phone: string; role: string };

interface Draft {
  displayName: string;
  caregiverFirstName: string;
  enjoys: string[];
  calms: string[];
  avoid: string[];
  rhythm: string;
  contacts: ContactDraft[];
}

export type SaveOutcome = { ok: true } | { ok: false; message: string };

interface Props {
  profile: Profile;
  copy: AppCopy["profile"];
  onSave: (body: ProfileBody) => Promise<SaveOutcome>;
  onCancel: () => void;
}

const toDraft = (p: Profile): Draft => ({
  displayName: p.displayName ?? "",
  caregiverFirstName: p.caregiverFirstName ?? "",
  enjoys: p.enjoys,
  calms: p.calms,
  avoid: p.avoid,
  rhythm: p.rhythm,
  contacts: p.contacts.map((c) => ({ name: c.name, phone: c.phone, role: c.role ?? "" })),
});

const phoneOk = (phone: string): boolean => {
  const digits = phone.replace(/\D/g, "").length;
  return (
    PHONE_PATTERN.test(phone.trim()) &&
    digits >= PROFILE_LIMITS.phoneMinDigits &&
    digits <= PROFILE_LIMITS.phoneMaxDigits
  );
};

/** Per-contact problem text, or null when the row is fine (or empty and will be dropped). */
function contactProblem(c: ContactDraft): string | null {
  const name = c.name.trim();
  const phone = c.phone.trim();
  if (!name && !phone) return null;
  if (!name || !phone) return PROFILE_TEXT.contactNeedsBoth;
  return phoneOk(phone) ? null : PROFILE_TEXT.contactBadPhone;
}

export function ProfileForm({ profile, copy, onSave, onCancel }: Props) {
  const initial = toDraft(profile);
  const [draft, setDraft] = useState<Draft>(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  const [confirmLeave, setConfirmLeave] = useState(false);
  const dirty = JSON.stringify(draft) !== JSON.stringify(initial);
  const set = <K extends keyof Draft>(key: K, value: Draft[K]): void =>
    setDraft((d) => ({ ...d, [key]: value }));

  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setChecked(true);
    if (draft.contacts.some((c) => contactProblem(c) !== null)) return;
    setSaving(true);
    setError(null);
    const contacts = draft.contacts
      .filter((c) => c.name.trim() || c.phone.trim())
      .map((c) => ({
        name: c.name.trim(),
        phone: c.phone.trim(),
        ...(c.role.trim() ? { role: c.role.trim() } : {}),
      }));
    const outcome = await onSave({
      displayName: draft.displayName.trim() || null,
      caregiverFirstName: draft.caregiverFirstName.trim() || null,
      enjoys: draft.enjoys,
      calms: draft.calms,
      avoid: draft.avoid,
      rhythm: draft.rhythm,
      contacts,
    });
    setSaving(false);
    if (!outcome.ok) setError(outcome.message);
  }

  function cancel(): void {
    if (dirty) setConfirmLeave(true);
    else onCancel();
  }

  const setContact = (index: number, patch: Partial<ContactDraft>): void =>
    set(
      "contacts",
      draft.contacts.map((c, i) => (i === index ? { ...c, ...patch } : c)),
    );

  return (
    <form className={styles.form} onSubmit={(event) => void submit(event)} noValidate>
      <p className={styles.hint}>{copy.editNote}</p>
      <div className={styles.field}>
        <label htmlFor="pf-name">{PROFILE_TEXT.nameLabel}</label>
        <p className={styles.hint}>{PROFILE_TEXT.nameHint}</p>
        <input
          id="pf-name"
          className={styles.input}
          value={draft.displayName}
          maxLength={PROFILE_LIMITS.displayName}
          onChange={(e) => set("displayName", e.target.value)}
        />
      </div>
      <ChipEditor title={copy.enjoysTitle} items={draft.enjoys} onChange={(v) => set("enjoys", v)} />
      <ChipEditor title={copy.calmsTitle} items={draft.calms} onChange={(v) => set("calms", v)} />
      <ChipEditor title={copy.avoidTitle} items={draft.avoid} onChange={(v) => set("avoid", v)} />
      <div className={styles.field}>
        <label htmlFor="pf-rhythm">{copy.rhythmTitle}</label>
        <p className={styles.hint}>{PROFILE_TEXT.rhythmHint}</p>
        <textarea
          id="pf-rhythm"
          className={styles.textarea}
          value={draft.rhythm}
          maxLength={PROFILE_LIMITS.rhythmLength}
          onChange={(e) => set("rhythm", e.target.value)}
        />
      </div>
      <fieldset className={styles.field} style={{ border: 0, padding: 0, margin: 0 }}>
        <legend>{copy.contactsTitle}</legend>
        {draft.contacts.map((contact, index) => {
          const problem = checked ? contactProblem(contact) : null;
          return (
            <div key={index} className={styles.contactBlock} role="group" aria-label={`${copy.contactsTitle} ${index + 1}`}>
              <label htmlFor={`pf-cn-${index}`}>{PROFILE_TEXT.contactName}</label>
              <input
                id={`pf-cn-${index}`}
                className={styles.input}
                value={contact.name}
                maxLength={PROFILE_LIMITS.contactName}
                onChange={(e) => setContact(index, { name: e.target.value })}
              />
              <label htmlFor={`pf-cp-${index}`}>{PROFILE_TEXT.contactPhone}</label>
              <input
                id={`pf-cp-${index}`}
                className={styles.input}
                type="tel"
                value={contact.phone}
                maxLength={PROFILE_LIMITS.phoneLength}
                onChange={(e) => setContact(index, { phone: e.target.value })}
              />
              <label htmlFor={`pf-cr-${index}`}>{PROFILE_TEXT.contactRole}</label>
              <input
                id={`pf-cr-${index}`}
                className={styles.input}
                value={contact.role}
                maxLength={PROFILE_LIMITS.contactRole}
                onChange={(e) => setContact(index, { role: e.target.value })}
              />
              {problem && (
                <p className={styles.fieldError} role="alert">
                  {problem}
                </p>
              )}
              <button
                type="button"
                className={styles.btn}
                aria-label={`${PROFILE_TEXT.contactRemove} ${index + 1}`}
                onClick={() => set("contacts", draft.contacts.filter((_, i) => i !== index))}
              >
                {PROFILE_TEXT.contactRemove}
              </button>
            </div>
          );
        })}
        {draft.contacts.length < PROFILE_LIMITS.contacts && (
          <button
            type="button"
            className={styles.btn}
            onClick={() => set("contacts", [...draft.contacts, { name: "", phone: "", role: "" }])}
          >
            {PROFILE_TEXT.contactsAdd}
          </button>
        )}
      </fieldset>
      <div className={styles.field}>
        <label htmlFor="pf-cg">{PROFILE_TEXT.caregiverNameLabel}</label>
        <input
          id="pf-cg"
          className={styles.input}
          value={draft.caregiverFirstName}
          maxLength={PROFILE_LIMITS.caregiverName}
          onChange={(e) => set("caregiverFirstName", e.target.value)}
        />
      </div>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {confirmLeave && (
        <div className={styles.confirm} role="alertdialog" aria-labelledby="pf-discard">
          <p id="pf-discard">{PROFILE_TEXT.discardTitle}</p>
          <div className={styles.row}>
            <button type="button" className={styles.btn} onClick={() => setConfirmLeave(false)}>
              {PROFILE_TEXT.discardKeep}
            </button>
            <button type="button" className={`${styles.btn} ${styles.danger}`} onClick={onCancel}>
              {PROFILE_TEXT.discardLeave}
            </button>
          </div>
        </div>
      )}
      <div className={styles.row}>
        <button type="submit" className={`${styles.btn} ${styles.primary}`} disabled={saving}>
          {saving ? PROFILE_TEXT.saving : PROFILE_TEXT.save}
        </button>
        <button type="button" className={styles.btn} onClick={cancel}>
          {PROFILE_TEXT.cancel}
        </button>
      </div>
    </form>
  );
}
