import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";

/** Stub: the real page replaces this file. Collects nothing, fetches nothing. */
export default function PlanPage() {
  return (
    <FunnelScreen>
      <Seo title={pageTitle("Your plan")} description="Kelper care plan." />
      <meta name="robots" content="noindex" />
      <h1 data-funnel-heading tabIndex={-1}>
        Your plan
      </h1>
    </FunnelScreen>
  );
}
