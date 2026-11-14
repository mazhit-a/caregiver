import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";

/** Stub: the real page replaces this file. Collects nothing, fetches nothing. */
export default function GiftPage() {
  return (
    <FunnelScreen>
      <Seo
        title={pageTitle("Your free phrase sheet")}
        description="Kelper care plan."
      />
      <meta name="robots" content="noindex" />
      <h1 data-funnel-heading tabIndex={-1}>
        Your free phrase sheet
      </h1>
    </FunnelScreen>
  );
}
