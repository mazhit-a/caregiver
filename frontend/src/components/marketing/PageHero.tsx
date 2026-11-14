import type { ReactNode } from "react";
import { ImageFigure } from "./ImageFigure";
import { Section } from "./Section";
import styles from "./PageHero.module.css";

interface Props {
  eyebrow?: string;
  title: string;
  lead: string;
  /** Actions and notes under the lead, e.g. a StartLink. */
  children?: ReactNode;
  image?: { src: string; alt: string; width: number; height: number };
}

/** Page opener: the only h1 on a page. Text first, image after it on small screens. */
export function PageHero({ eyebrow, title, lead, children, image }: Props) {
  return (
    <Section>
      <div className={styles.hero}>
        <div className={styles.text}>
          {eyebrow ? <p className={styles.eyebrow}>{eyebrow}</p> : null}
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.lead}>{lead}</p>
          {children}
        </div>
        {image ? (
          <div className={styles.image}>
            <ImageFigure {...image} loading="eager" />
          </div>
        ) : null}
      </div>
    </Section>
  );
}
