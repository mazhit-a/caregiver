import { CtaBand } from "../../components/marketing/CtaBand";
import { NumberedSteps } from "../../components/marketing/NumberedSteps";
import { PageHero } from "../../components/marketing/PageHero";
import { Section } from "../../components/marketing/Section";
import { PRACTICE_COPY as C } from "../../content/practice";
import { Seo } from "../../layout/Seo";
import ollie from "../../assets/practice/ollie-thumbs-up.webp";
import { PracticeDemo } from "./PracticeDemo";
import styles from "./PracticePage.module.css";

export default function PracticePage() {
  return (
    <>
      <Seo title={C.seoTitle} description={C.seoDescription} />
      <PageHero
        title={C.hero.title}
        lead={C.hero.lead}
        image={{ src: ollie, alt: C.hero.imageAlt, width: 432, height: 640 }}
      />
      <Section>
        <PracticeDemo />
      </Section>
      <Section variant="muted" labelledBy="pattern-title">
        <div className={styles.stack}>
          <h2 id="pattern-title" className={styles.h2}>
            {C.pattern.title}
          </h2>
          <NumberedSteps
            steps={C.pattern.steps.map((s) => ({
              title: s.title,
              text: (
                <>
                  <span className={styles.example}>{s.example}</span>
                  <span className={styles.why}>{s.why}</span>
                </>
              ),
            }))}
          />
        </div>
      </Section>
      <Section>
        <div className={styles.boundaries}>
          <div className={styles.stack}>
            <h2 className={styles.h2}>{C.real.title}</h2>
            <ul className={styles.list}>
              {C.real.items.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>{C.not.title}</h2>
            {C.not.items.map((t) => (
              <p key={t} className={styles.body}>
                {t}
              </p>
            ))}
          </div>
        </div>
      </Section>
      <Section>
        <CtaBand title={C.cta.title} />
      </Section>
    </>
  );
}
