import { useState } from "react";
import { Outlet } from "react-router";
import { HelpSheet } from "./HelpSheet";
import { ScrollManager } from "./ScrollManager";
import { SiteFooter } from "./SiteFooter";
import { SiteHeader } from "./SiteHeader";
import { SkipLink } from "./SkipLink";
import styles from "./RootLayout.module.css";

export function RootLayout() {
  const [helpOpen, setHelpOpen] = useState(false);
  return (
    <div className={styles.shell}>
      <SkipLink />
      <SiteHeader onNeedHelp={() => setHelpOpen(true)} />
      <main id="main" tabIndex={-1} className={styles.main}>
        <Outlet />
      </main>
      <SiteFooter />
      <HelpSheet open={helpOpen} onClose={() => setHelpOpen(false)} />
      <ScrollManager />
    </div>
  );
}
