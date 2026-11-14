import { Seo, pageTitle } from "../../../layout/Seo";

/** Stub: G16 replaces this file. Outside AppLayout, because the session is gone by then. */
export default function GoodbyePage() {
  return (
    <main id="main" tabIndex={-1}>
      <Seo
        title={pageTitle("Goodbye")}
        description="Your data has been deleted."
      />
      <meta name="robots" content="noindex" />
      <h1 data-app-heading tabIndex={-1}>
        Goodbye
      </h1>
    </main>
  );
}
