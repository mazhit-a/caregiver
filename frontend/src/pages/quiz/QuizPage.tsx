import { Link } from "react-router";
import { Seo, pageTitle } from "../../layout/Seo";
import styles from "../NotFoundPage.module.css";
import { ROUTES } from "../../routes";

/** Placeholder: the quiz arrives in a later batch, which replaces this file. Collects nothing. */
export default function QuizPage() {
  return (
    <div className={styles.page}>
      <Seo title={pageTitle("Quiz")} description="The Kelper quiz is coming soon." />
      <h1 className={styles.title}>The quiz is coming soon</h1>
      <p>This version of Kelper does not have the quiz yet. Nothing you do here is saved.</p>
      <p>
        <Link to={ROUTES.home}>Back to the home page</Link>
      </p>
    </div>
  );
}
