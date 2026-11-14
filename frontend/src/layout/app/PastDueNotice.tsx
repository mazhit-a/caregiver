import { Link } from "react-router";
import { ROUTES } from "../../routes";
import styles from "./AppLayout.module.css";

interface Props {
  /** The server's own message (402 past_due). */
  message?: string;
  settingsLabel: string;
}

const FALLBACK = "Your last payment did not go through.";

/** Shown by AppLayout only. The paywall would invite a second subscription, so this stays in the shell. */
export function PastDueNotice({ message, settingsLabel }: Props) {
  return (
    <div className={styles.notice} role="status">
      <p>{message?.trim() ? message : FALLBACK}</p>
      <Link to={ROUTES.settings} className={styles.noticeLink}>
        {settingsLabel}
      </Link>
    </div>
  );
}
