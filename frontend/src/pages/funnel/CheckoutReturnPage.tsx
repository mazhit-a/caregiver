import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";

/** Stub: the real page replaces this file. Collects nothing, fetches nothing. */
export default function CheckoutReturnPage() {
  return (
    <FunnelScreen>
      <Seo
        title={pageTitle("Checking your payment")}
        description="Kelper care plan."
      />
      <meta name="robots" content="noindex" />
      <h1 data-funnel-heading tabIndex={-1}>
        Checking your payment
      </h1>
    </FunnelScreen>
  );
}
