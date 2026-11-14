import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";

/** Stub for `/quiz/:questionId`: F5 replaces this file. */
export default function QuizStepPage() {
  return (
    <FunnelScreen>
      <Seo title={pageTitle("Quiz")} description="Kelper quiz." />
      <meta name="robots" content="noindex" />
      <h1 data-funnel-heading tabIndex={-1}>
        Quiz
      </h1>
    </FunnelScreen>
  );
}
