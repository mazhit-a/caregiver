import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";

/**
 * Placeholder: the Today batch replaces this file (default export `TodayPage`, route `/today`).
 * Collects nothing and fetches nothing. The API-rendered success line needs the funnel-copy call,
 * which the pages that own it show; here a fixed placeholder-free line is used.
 */
export default function TodayPage() {
  return (
    <FunnelScreen>
      <Seo
        title={pageTitle("Today")}
        description="Your daily plan is coming soon."
      />
      <meta name="robots" content="noindex" />
      <h1 data-funnel-heading tabIndex={-1}>
        Today is coming soon
      </h1>
      <p>You’re all set.</p>
    </FunnelScreen>
  );
}
