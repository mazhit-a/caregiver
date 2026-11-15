import { useEffect, useState } from "react";
import { getCareCard, publishCareCard, revokeCareCard, updateCareCard } from "../../../api/app";
import type { CareCard } from "../../../api/appTypes";
import { ApiError } from "../../../api/client";
import { useAppCopy } from "../../../api/AppDataProvider";
import { useAppAction, useAppRequest } from "../../../api/useAppRequest";
import { StatusBlock } from "../../../components/StatusBlock";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import { CARD_STATUS_LABEL, CARE_CARD_TEXT } from "../../../content/app/careCard";
import { formatDate } from "../../../format/date";
import { Seo, pageTitle } from "../../../layout/Seo";
import { CardPreview } from "./CardPreview";
import { LinkField } from "./LinkField";
import { PhrasePicker } from "./PhrasePicker";
import styles from "./careCard.module.css";

const CHIP_CLASS: Record<CareCard["status"], string> = {
  not_published: "",
  published: styles.chipPublished ?? "",
  update_available: styles.chipUpdate ?? "",
  revoked: styles.chipRevoked ?? "",
};

export default function CareCardPage() {
  const act = useAppAction();
  const copy = useAppCopy();
  const card = useAppRequest(getCareCard, []);
  const [chosen, setChosen] = useState<string[]>([]);
  const [busy, setBusy] = useState<"publish" | "update" | "revoke" | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<{ kind: "error" | "notice"; text: string } | null>(null);

  const loaded = card.status === "ready" ? card.data : null;
  useEffect(() => {
    if (loaded) setChosen(loaded.chosenPhraseIds);
  }, [loaded]);

  if (card.handled) return null;
  if (copy.status === "error" || card.status === "error") {
    return (
      <StatusBlock
        status="error"
        what={CARE_CARD_TEXT.loadingWhat}
        onRetry={() => {
          copy.refresh();
          card.retry();
        }}
      />
    );
  }
  if (copy.status === "loading" || card.status === "loading" || !loaded) {
    return <StatusBlock status="loading" what={CARE_CARD_TEXT.loadingWhat} onRetry={() => undefined} />;
  }

  const text = copy.data.careCard;
  const live = loaded.status === "published" || loaded.status === "update_available";

  async function run(kind: "publish" | "update" | "revoke"): Promise<void> {
    setBusy(kind);
    setMessage(null);
    let serverMessage: string | null = null;
    let code: string | null = null;
    const result = await act(async () => {
      try {
        if (kind === "publish") return await publishCareCard(chosen);
        if (kind === "update") return await updateCareCard(chosen);
        return await revokeCareCard();
      } catch (error) {
        if (error instanceof ApiError) {
          serverMessage = error.message;
          code = error.code;
        }
        throw error;
      }
    });
    setBusy(null);
    setConfirming(false);
    if (result.ok) {
      card.retry();
      return;
    }
    if (result.handled) return;
    if (code === "card_already_published" || code === "card_not_published") {
      setMessage({
        kind: "notice",
        text: code === "card_already_published" ? CARE_CARD_TEXT.conflictAlready : CARE_CARD_TEXT.conflictNotShared,
      });
      card.retry();
      return;
    }
    setMessage({ kind: "error", text: serverMessage ?? APP_ERROR_MESSAGES[result.failure.kind] });
  }

  const disabled = busy !== null;
  const newCount = loaded.newPhraseCount;

  return (
    <div className={styles.page}>
      <Seo title={pageTitle(text.title)} description={text.purpose} />
      <meta name="robots" content="noindex" />
      <header className={`${styles.header} ${styles.noPrint}`}>
        <h1 data-app-heading tabIndex={-1}>
          {text.title}
        </h1>
        <p className={styles.purpose}>{text.purpose}</p>
      </header>

      <div className={`${styles.statusRow} ${styles.noPrint}`}>
        <span className={styles.statusLabel}>{CARE_CARD_TEXT.statusLabel}:</span>
        <span className={`${styles.chip} ${CHIP_CLASS[loaded.status]}`}>{CARD_STATUS_LABEL[loaded.status]}</span>
        {live && (
          <span className={styles.statusLabel}>
            {loaded.lastOpenedAt
              ? CARE_CARD_TEXT.lastOpened(formatDate(loaded.lastOpenedAt))
              : CARE_CARD_TEXT.notOpened}
          </span>
        )}
      </div>

      <section className={styles.section} aria-labelledby="preview-title">
        <h2 id="preview-title" className={styles.noPrint}>
          {CARE_CARD_TEXT.previewTitle}
        </h2>
        <p className={`${styles.hint} ${styles.noPrint}`}>{CARE_CARD_TEXT.previewNote}</p>
        <CardPreview card={loaded.preview} />
      </section>

      <div className={`${styles.section} ${styles.noPrint}`}>
        {loaded.status === "update_available" && (
          <p className={styles.notice}>
            {newCount === 1
              ? CARE_CARD_TEXT.newPhrasesOne
              : newCount > 1
                ? CARE_CARD_TEXT.newPhrasesMany(newCount)
                : CARE_CARD_TEXT.updateHint}
          </p>
        )}
        {loaded.status === "revoked" && <p className={styles.notice}>{CARE_CARD_TEXT.revoked}</p>}
        {message && (
          <p className={message.kind === "error" ? styles.error : styles.notice} role="alert">
            {message.text}
          </p>
        )}

        <PhrasePicker available={loaded.availablePhrases} chosen={chosen} onChange={setChosen} />

        <p className={styles.hint}>{text.sharingSentence}</p>
        <div className={styles.row}>
          {!live && (
            <button
              type="button"
              className={`${styles.btn} ${styles.primary}`}
              aria-disabled={disabled}
              onClick={() => !disabled && void run("publish")}
            >
              {busy === "publish"
                ? CARE_CARD_TEXT.publishing
                : loaded.status === "revoked"
                  ? CARE_CARD_TEXT.publishNew
                  : CARE_CARD_TEXT.publish}
            </button>
          )}
          {live && (
            <button
              type="button"
              className={`${styles.btn} ${loaded.status === "update_available" ? styles.primary : ""}`}
              aria-disabled={disabled}
              onClick={() => !disabled && void run("update")}
            >
              {busy === "update" ? CARE_CARD_TEXT.updating : CARE_CARD_TEXT.update}
            </button>
          )}
          {live && !confirming && (
            <button
              type="button"
              className={`${styles.btn} ${styles.danger}`}
              disabled={disabled}
              onClick={() => setConfirming(true)}
            >
              {CARE_CARD_TEXT.revoke}
            </button>
          )}
          <button type="button" className={styles.btn} onClick={() => window.print()}>
            {CARE_CARD_TEXT.print}
          </button>
        </div>
        <p className={styles.hint}>{CARE_CARD_TEXT.printNote}</p>

        {confirming && (
          <div className={styles.confirm} role="alertdialog" aria-labelledby="revoke-title" aria-describedby="revoke-body">
            <h3 id="revoke-title">{CARE_CARD_TEXT.revokeTitle}</h3>
            <p id="revoke-body">{CARE_CARD_TEXT.revokeBody}</p>
            <div className={styles.row}>
              <button type="button" className={styles.btn} onClick={() => setConfirming(false)}>
                {CARE_CARD_TEXT.revokeKeep}
              </button>
              <button
                type="button"
                className={`${styles.btn} ${styles.danger}`}
                aria-disabled={disabled}
                onClick={() => !disabled && void run("revoke")}
              >
                {CARE_CARD_TEXT.revokeConfirm}
              </button>
            </div>
          </div>
        )}

        {live && loaded.link && <LinkField link={loaded.link} />}
      </div>
    </div>
  );
}
