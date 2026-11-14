import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";

/** Stub: the real page replaces this file. Collects nothing, fetches nothing. */
export default function PaywallPage() {
  return (
    <FunnelScreen>
      <Seo
        title={pageTitle("Start your plan")}
        description="Kelper care plan."
      />
      <meta name="robots" content="noindex" />
      <h1 data-funnel-heading tabIndex={-1}>
        Start your plan
      </h1>
    </FunnelScreen>
  );
}
