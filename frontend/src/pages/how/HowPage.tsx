import ollie from "../../assets/how/ollie-explaining.webp";
import quizPhone from "../../assets/how/quiz-phone.webp";
import todayPhone from "../../assets/how/today-phone.webp";
import { CtaBand } from "../../components/marketing/CtaBand";
import { ImageFigure } from "../../components/marketing/ImageFigure";
import { NumberedSteps } from "../../components/marketing/NumberedSteps";
import { PageHero } from "../../components/marketing/PageHero";
import { Section } from "../../components/marketing/Section";
import {
  HOW_CTA,
  HOW_HERO,
  HOW_SEO,
  HOW_STEP1,
  HOW_STEP2,
  HOW_STEP3,
  HOW_STEP4,
  HOW_STEP5,
} from "../../content/how";
import { Seo } from "../../layout/Seo";
import styles from "./HowPage.module.css";

function StepHeading({ id, eyebrow, title, lead }: { id: string; eyebrow: string; title: string; lead: string }) {
  return (
    <>
      <p className={styles.eyebrow}>{eyebrow}</p>
      <h2 id={id} className={styles.h2}>
        {title}
      </h2>
      <p className={styles.lead}>{lead}</p>
    </>
  );
}

export default function HowPage() {
  return (
    <>
      <Seo title={HOW_SEO.title} description={HOW_SEO.description} />
      <div className={styles.hero}>
        <PageHero
          title={HOW_HERO.title}
          lead={HOW_HERO.lead}
          image={{ src: ollie, alt: "Ollie explaining with one paw raised", width: 440, height: 640 }}
        />
      </div>

      <Section labelledBy="how-step1">
        <div className={styles.row}>
          <div className={styles.text}>
            <StepHeading id="how-step1" eyebrow={HOW_STEP1.eyebrow} title={HOW_STEP1.title} lead={HOW_STEP1.lead} />
            <ul className={styles.chips} aria-label="What the questions cover">
              {HOW_STEP1.topics.map((topic) => (
                <li key={topic} className={styles.chip}>
                  {topic}
                </li>
              ))}
            </ul>
            <p className={styles.note}>{HOW_STEP1.note}</p>
          </div>
          <div className={`${styles.phoneFrame} ${styles.butterFrame}`}>
            <ImageFigure
              src={quizPhone}
              alt={HOW_STEP1.imageAlt}
              width={560}
              height={896}
              className={styles.phone}
            />
          </div>
        </div>
      </Section>

      <Section labelledBy="how-step2">
        <div className={styles.row}>
          <div className={styles.text}>
            <StepHeading id="how-step2" eyebrow={HOW_STEP2.eyebrow} title={HOW_STEP2.title} lead={HOW_STEP2.lead} />
          </div>
          <div className={styles.exampleCard}>
            <p className={styles.exampleLabel}>{HOW_STEP2.exampleLabel}</p>
            <div className={styles.heard}>
              <h3 className={styles.cardTitle}>{HOW_STEP2.heardTitle}</h3>
              <p className={styles.heardText}>{HOW_STEP2.heardText}</p>
            </div>
            <div className={styles.course}>
              <h3 className={styles.cardTitle}>{HOW_STEP2.courseTitle}</h3>
              <ol className={styles.courseList}>
                {HOW_STEP2.course.map((item) => (
                  <li key={item.title} className={styles.courseItem}>
                    <span className={styles.courseText}>
                      <span className={styles.courseTitle}>{item.title}</span>
                      <span className={styles.courseWhy}>{item.why}</span>
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      </Section>

      <Section variant="muted" labelledBy="how-step3">
        <div className={styles.stack}>
          <div className={`${styles.text} ${styles.wide}`}>
            <StepHeading id="how-step3" eyebrow={HOW_STEP3.eyebrow} title={HOW_STEP3.title} lead={HOW_STEP3.lead} />
          </div>
          <NumberedSteps steps={HOW_STEP3.steps} columns={4} />
        </div>
      </Section>

      <Section labelledBy="how-step4">
        <div className={styles.stack}>
          <div className={`${styles.text} ${styles.wide}`}>
            <StepHeading id="how-step4" eyebrow={HOW_STEP4.eyebrow} title={HOW_STEP4.title} lead={HOW_STEP4.lead} />
          </div>
          <table className={styles.table}>
            <caption className={styles.caption}>{HOW_STEP4.tableCaption}</caption>
            <thead>
              <tr>
                {HOW_STEP4.columns.map((column) => (
                  <th key={column} scope="col">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {HOW_STEP4.rows.map(([where, moment, todo]) => (
                <tr key={where}>
                  <th scope="row">{where}</th>
                  <td data-label={HOW_STEP4.columns[1]}>{moment}</td>
                  <td data-label={HOW_STEP4.columns[2]}>{todo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section labelledBy="how-step5">
        <div className={styles.row}>
          <div className={styles.text}>
            <StepHeading id="how-step5" eyebrow={HOW_STEP5.eyebrow} title={HOW_STEP5.title} lead={HOW_STEP5.lead} />
            <p className={styles.note}>{HOW_STEP5.note}</p>
          </div>
          <div className={`${styles.phoneFrame} ${styles.irisFrame}`}>
            <ImageFigure
              src={todayPhone}
              alt={HOW_STEP5.imageAlt}
              width={560}
              height={896}
              className={styles.phone}
            />
          </div>
        </div>
      </Section>

      <Section>
        <CtaBand title={HOW_CTA.title} />
      </Section>
    </>
  );
}
