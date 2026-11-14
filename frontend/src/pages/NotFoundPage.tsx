import { Link } from "react-router";
import { Seo, pageTitle } from "../layout/Seo";
import { ROUTES } from "../routes";
import styles from "./NotFoundPage.module.css";

export default function NotFoundPage() {
  return (
    <div className={styles.page}>
      <Seo title={pageTitle("Page not found")} description="That page does not exist." />
      <meta name="robots" content="noindex" />
      <h1 className={styles.title}>We can’t find that page</h1>
      <p>The link may be old or mistyped. Here are two ways forward.</p>
      <p className={styles.links}>
        <Link to={ROUTES.home}>Go to the home page</Link>
        <Link to={ROUTES.quiz}>Get Mom’s plan</Link>
      </p>
    </div>
  );
}
