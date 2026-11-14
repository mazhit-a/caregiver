import { useState } from "react";
import { clearMyData } from "../../../api/app";
import { CLEAR } from "../../../content/app/exit";
import { ExitFlow } from "./ExitFlow";
import styles from "./settings.module.css";

/** The "Clear my data" entry of the Privacy card; opens a two-step confirmation in place. */
export function ClearDataSection() {
  const [open, setOpen] = useState(false);
  if (open) {
    return (
      <ExitFlow
        labels={{ ...CLEAR, facts: CLEAR.step1Facts }}
        headings={[CLEAR.title, CLEAR.title]}
        blocked={CLEAR.failed}
        onBack={() => setOpen(false)}
        run={async () => ({ kind: "cleared", ...(await clearMyData()) })}
      />
    );
  }
  return (
    <div className={styles.actions}>
      <button type="button" className={styles.secondary} onClick={() => setOpen(true)}>
        {CLEAR.open}
      </button>
    </div>
  );
}
