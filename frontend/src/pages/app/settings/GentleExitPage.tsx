import { useNavigate } from "react-router";
import { gentleExit } from "../../../api/app";
import { useAppCopy } from "../../../api/AppDataProvider";
import { EXIT } from "../../../content/app/exit";
import { Seo, pageTitle } from "../../../layout/Seo";
import { ROUTES } from "../../../routes";
import { ExitFlow } from "./ExitFlow";
import styles from "./settings.module.css";

export default function GentleExitPage() {
  const navigate = useNavigate();
  const copy = useAppCopy();
  const title = copy.data?.settings.gentleExitEntry ?? EXIT.title;
  return (
    <div className={styles.page}>
      <Seo title={pageTitle(EXIT.title)} description={EXIT.title} />
      <meta name="robots" content="noindex" />
      <h1 className={styles.title} data-app-heading tabIndex={-1}>
        {title}
      </h1>
      <ExitFlow
        labels={{ ...EXIT, facts: EXIT.step1Facts }}
        headings={[EXIT.step1Heading, EXIT.step2Heading]}
        blocked={EXIT.blocked}
        onBack={() => navigate(ROUTES.settings)}
        run={async () => ({ kind: "exit", ...(await gentleExit()) })}
      />
    </div>
  );
}
