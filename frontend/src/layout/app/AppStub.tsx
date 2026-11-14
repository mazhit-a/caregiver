import type { ReactNode } from "react";
import { Seo, pageTitle } from "../Seo";

interface Props {
  title: string;
  children?: ReactNode;
}

/** Placeholder page for routes whose increment has not landed: h1, Seo, noindex, no fetch. */
export function AppStub({ title, children }: Props) {
  return (
    <>
      <Seo title={pageTitle(title)} description={`${title} is coming soon.`} />
      <meta name="robots" content="noindex" />
      <h1 data-app-heading tabIndex={-1}>
        {title}
      </h1>
      {children}
    </>
  );
}
