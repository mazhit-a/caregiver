import type { ReactNode } from "react";
import { Link } from "react-router";
import logo from "../../assets/kelper-logo.svg";
import { NEED_HELP_NOW } from "../nav";
import { ROUTES } from "../../routes";
import { useFunnelContext } from "./FunnelLayout";
import { useStepFocus } from "./useStepFocus";
import styles from "./FunnelScreen.module.css";

type Back = { to: string } | { onClick: () => void };

interface Props {
  /** Optional Back button: a link to the previous step, or a handler. Hidden when omitted. */
  back?: Back;
  /** Optional progress bar, shown under the header row. */
  progress?: ReactNode;
  /** Optional sticky action bar content (primary and secondary buttons). */
  actionBar?: ReactNode;
  children: ReactNode;
}

const BACK_LABEL = "Back"; // content/funnel-copy.json common.back (F3 mirrors it)

/** Header row, the only <main>, and an optional sticky bottom bar. Pages supply the h1. */
export function FunnelScreen({ back, progress, actionBar, children }: Props) {
  const { openHelp, shouldFocusStep } = useFunnelContext();
  useStepFocus(shouldFocusStep);

  return (
    <>
      <header className={styles.header}>
        <div className={styles.row}>
          <div className={styles.side}>
            {back && "to" in back && (
              <Link to={back.to} className={styles.back}>
                {BACK_LABEL}
              </Link>
            )}
            {back && "onClick" in back && (
              <button
                type="button"
                className={styles.back}
                onClick={back.onClick}
              >
                {BACK_LABEL}
              </button>
            )}
          </div>
          <Link
            to={ROUTES.home}
            className={styles.logo}
            aria-label="Kelper home"
          >
            <img src={logo} alt="" width={96} height={36} />
          </Link>
          <div className={`${styles.side} ${styles.end}`}>
            <button type="button" className={styles.help} onClick={openHelp}>
              {NEED_HELP_NOW}
            </button>
          </div>
        </div>
        {progress && <div className={styles.progress}>{progress}</div>}
      </header>
      <main id="main" tabIndex={-1} className={styles.main}>
        {children}
      </main>
      {actionBar && (
        <div className={styles.bar}>
          <div className={styles.barInner}>{actionBar}</div>
        </div>
      )}
    </>
  );
}
