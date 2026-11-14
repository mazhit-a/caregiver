import type { ReactNode } from "react";
import styles from "./Section.module.css";

export type SectionVariant = "plain" | "butter" | "plum" | "muted";

interface Props {
  variant?: SectionVariant;
  id?: string;
  /** Id of the heading that names this section (makes it a landmark region). */
  labelledBy?: string;
  children: ReactNode;
}

/** Full-width band with a centred 1120px wrapper. Plum text is light-on-dark. */
export function Section({ variant = "plain", id, labelledBy, children }: Props) {
  return (
    <section id={id} aria-labelledby={labelledBy} className={`${styles.section} ${styles[variant]}`}>
      <div className={styles.inner}>{children}</div>
    </section>
  );
}
