import { useEffect, useRef } from "react";
import { NEED_HELP_NOW, NOT_MEDICAL_ADVICE } from "./nav";
import { useCrisisList } from "./useCrisisList";
import styles from "./HelpSheet.module.css";

interface Props {
  open: boolean;
  onClose: () => void;
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
        <p className={styles.note}>{NOT_MEDICAL_ADVICE}</p>
        <button type="button" className={styles.close} onClick={() => ref.current?.close()}>
          Close
        </button>
      </div>
    </dialog>
  );
}
