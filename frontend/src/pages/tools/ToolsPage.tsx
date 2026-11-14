import ollieNotebook from "../../assets/tools/ollie-notebook.webp";
import { CtaBand } from "../../components/marketing/CtaBand";
import { FeatureRow } from "../../components/marketing/FeatureRow";
import { ImageFigure } from "../../components/marketing/ImageFigure";
import { Section } from "../../components/marketing/Section";
import {
  CARE_CARD,
  MOMS_PAGE,
  PHRASE_SHEET,
  TOOLS_CTA,
  TOOLS_HERO,
  TOOLS_SEO,
  VISIT_SHEET,
} from "../../content/tools";
import { Seo } from "../../layout/Seo";
import styles from "./ToolsPage.module.css";

export default function ToolsPage() {
  return (
    <>
      <Seo {...TOOLS_SEO} />
      <Section>
        <div className={styles.hero}>
          <div className={styles.heroText}>
            <h1 className={styles.heroTitle}>{TOOLS_HERO.title}</h1>
            <p className={styles.heroLead}>{TOOLS_HERO.lead}</p>
          </div>
          <ImageFigure
            src={ollieNotebook}
            alt={TOOLS_HERO.image.alt}
            width={TOOLS_HERO.image.width}
            height={TOOLS_HERO.image.height}
            loading="eager"
            className={styles.heroImage}
          />
        </div>
      </Section>

      <Section>
        <FeatureRow
          title={MOMS_PAGE.title}
          visual={
            <figure className={styles.figure}>
              <div className={styles.fields}>
                {MOMS_PAGE.fields.map((f) => (
                  <div key={f.label} className={`${styles.field} ${styles[f.tone]}`}>
                    <p className={styles.label}>{f.label}</p>
                    <p className={styles.value}>{f.value}</p>
                  </div>
                ))}
                <div className={styles.phrases}>
                  <p className={styles.label}>{MOMS_PAGE.phrasesLabel}</p>
                  {MOMS_PAGE.phrases.map((p) => (
                    <p key={p} className={styles.value}>
                      {p}
                    </p>
                  ))}
                </div>
              </div>
              <figcaption className={styles.caption}>{MOMS_PAGE.caption}</figcaption>
            </figure>
          }
        >
          <p className={styles.lead}>{MOMS_PAGE.lead}</p>
          <p className={styles.small}>{MOMS_PAGE.privacy}</p>
        </FeatureRow>
      </Section>

      <div className={styles.band}>
        <Section>
          <FeatureRow
            title={CARE_CARD.title}
            reverse
            visual={
              <figure className={styles.figure}>
                <div className={styles.card}>
                  <p className={styles.cardMeta}>{CARE_CARD.mock.updated}</p>
                  <h3 className={styles.cardTitle}>{CARE_CARD.mock.title}</h3>
                  {CARE_CARD.mock.sections.map((s) => (
                    <div key={s.label}>
                      <p className={styles.label}>{s.label}</p>
                      <p className={styles.value}>{s.value}</p>
                    </div>
                  ))}
                  <div className={styles.contacts}>
                    <p className={styles.label}>{CARE_CARD.mock.contactsLabel}</p>
                    <p className={styles.value}>{CARE_CARD.mock.contacts}</p>
                  </div>
                </div>
                <figcaption className={styles.caption}>{CARE_CARD.caption}</figcaption>
              </figure>
            }
          >
            <p className={styles.lead}>{CARE_CARD.lead}</p>
            <ul className={styles.bullets}>
              {CARE_CARD.bullets.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </FeatureRow>
        </Section>
      </div>

      <Section>
        <FeatureRow
          title={VISIT_SHEET.title}
          visual={
            <figure className={styles.figure}>
              <div className={styles.sheet}>
                <div className={styles.sheetHead}>
                  <p className={styles.sheetTitle}>{VISIT_SHEET.mock.title}</p>
                  <p className={styles.sheetWhen}>{VISIT_SHEET.mock.when}</p>
                </div>
                <div>
                  <p className={styles.label}>{VISIT_SHEET.mock.notesLabel}</p>
                  <p className={styles.sheetText}>{VISIT_SHEET.mock.notes}</p>
                </div>
                <div>
                  <p className={styles.label}>{VISIT_SHEET.mock.questionsLabel}</p>
                  <ol className={styles.questions}>
                    {VISIT_SHEET.mock.questions.map((q) => (
                      <li key={q}>{q}</li>
                    ))}
                  </ol>
                </div>
                <div className={styles.answers}>
                  <p className={styles.label}>{VISIT_SHEET.mock.answersLabel}</p>
                  <div className={styles.answerLine} aria-hidden="true" />
                </div>
                <p className={styles.sheetNote}>{VISIT_SHEET.note}</p>
              </div>
              <figcaption className={styles.caption}>{VISIT_SHEET.caption}</figcaption>
            </figure>
          }
        >
          <p className={styles.lead}>{VISIT_SHEET.lead}</p>
          <p className={styles.small}>{VISIT_SHEET.note}</p>
        </FeatureRow>
      </Section>

      <Section>
        <div className={styles.phraseBlock}>
          <div className={styles.phraseText}>
            <h2 className={styles.phraseTitle}>{PHRASE_SHEET.title}</h2>
            <p className={styles.lead}>{PHRASE_SHEET.lead}</p>
          </div>
          <ul className={styles.samples}>
            {PHRASE_SHEET.samples.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      </Section>

      <Section>
        <CtaBand title={TOOLS_CTA.title} ctaLabel={TOOLS_CTA.label} />
      </Section>
    </>
  );
}
