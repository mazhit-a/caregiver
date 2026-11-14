import type { ReactNode } from "react";
import styles from "./FeatureRow.module.css";

interface Props {
  eyebrow?: string;
  title: string;
  /** Text side: paragraphs, lists, links. */
  children: ReactNode;
  /** Visual side: image or decorative mock. */
  visual: ReactNode;
  /** Layout only: puts the visual first on wide screens. DOM order stays text, then visual. */
  reverse?: boolean;
}

export function FeatureRow({ eyebrow, title, children, visual, reverse = false }: Props) {
  return (
    <div className={reverse ? `${styles.row} ${styles.reverse}` : styles.row}>
      <div className={styles.text}>
        {eyebrow ? <p className={styles.eyebrow}>{eyebrow}</p> : null}
        <h2 className={styles.title}>{title}</h2>
        {children}
      </div>
      <div className={styles.visual}>{visual}</div>
    </div>
  );
}
