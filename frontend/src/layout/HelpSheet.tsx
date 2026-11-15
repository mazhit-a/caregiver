import { useEffect, useRef } from "react";
import { Link } from "react-router";
import { getGuides } from "../api/guides";
import { useRequest } from "../api/useRequest";
import { GUIDES_TEXT, guideRoute } from "../content/app/guides";
import { NEED_HELP_NOW } from "./nav";
import { useCrisisList } from "./useCrisisList";
import styles from "./HelpSheet.module.css";

interface Props {
  open: boolean;
  onClose: () => void;
}

/**
 * Additive list of the quick guides. Hidden while loading and on any failure: the crisis numbers
 * above never wait for it. It loads when the sheet is opened (it is only mounted then).
 */
function GuideLinks({ onNavigate }: { onNavigate: () => void }) {
  const request = useRequest((signal) => getGuides(signal), []);
  if (request.status !== "ready" || request.data.guides.length === 0) return null;
  return (
    <section aria-labelledby="help-guides-title" className={styles.guides}>
      <h3 id="help-guides-title" className={styles.guidesTitle}>
        {GUIDES_TEXT.helpSheetTitle}
      </h3>
      <ul className={styles.guideList}>
        {request.data.guides.map((g) => (
          <li key={g.id}>
            <Link to={guideRoute(g.id)} className={styles.guideLink} onClick={onNavigate}>
              {g.title}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Native modal dialog: the platform provides the focus trap and Esc. */
export function HelpSheet({ open, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLElement | null>(null);
  const resources = useCrisisList();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      trigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  const handleClose = (): void => {
    onClose();
    trigger.current?.focus();
  };

  return (
    // The dialog's own Esc handling covers keyboard users; the click is only a backdrop shortcut.
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions
    <dialog
      ref={ref}
      className={styles.sheet}
      aria-labelledby="help-title"
      onClose={handleClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) e.currentTarget.close();
      }}
    >
      <div className={styles.body}>
        <h2 id="help-title" className={styles.title}>
          {NEED_HELP_NOW}
        </h2>
        <ul className={styles.list}>
          {resources.map((r) => (
            <li key={r.id} className={styles.item}>
              <a href={`tel:${r.phone.replace(/[^\d+]/g, "")}`} className={styles.call}>
                <span className={styles.name}>{r.name}</span>
                <span className={styles.phone}>{r.phone}</span>
              </a>
              <p className={styles.desc}>{r.description}</p>
            </li>
          ))}
        </ul>
        {open && <GuideLinks onNavigate={() => ref.current?.close()} />}
        <button type="button" className={styles.close} onClick={() => ref.current?.close()}>
          Close
        </button>
      </div>
    </dialog>
  );
}
