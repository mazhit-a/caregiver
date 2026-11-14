import type { ReactNode } from "react";
import { StartLink } from "./StartLink";
import styles from "./CtaBand.module.css";

interface Props {
  title: string;
  text?: string;
  /** Button label; StartLink's default when omitted. */
  ctaLabel?: string;
  /** Optional picture beside the text. */
  visual?: ReactNode;
}

export function CtaBand({ title, text, ctaLabel, visual }: Props) {
  return (
    <div className={styles.band}>
      <div className={styles.text}>
        <h2 className={styles.title}>{title}</h2>
        {text ? <p className={styles.lead}>{text}</p> : null}
        <StartLink>{ctaLabel}</StartLink>
      </div>
      {visual ? <div className={styles.visual}>{visual}</div> : null}
    </div>
  );
}
