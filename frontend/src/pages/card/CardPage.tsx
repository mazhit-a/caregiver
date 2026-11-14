import { Seo, pageTitle } from "../../layout/Seo";

/** Stub: G17 replaces this file. Public page: own layout, no session logic. */
export default function CardPage() {
  return (
    <main id="main" tabIndex={-1}>
      <Seo title={pageTitle("Care card")} description="A shared care card." />
      <meta name="robots" content="noindex" />
      <h1>Care card</h1>
    </main>
  );
}
