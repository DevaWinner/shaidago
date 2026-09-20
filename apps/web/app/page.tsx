import type { ReactNode } from "react";

import { FirstViewport } from "@/components/landing/first-viewport";
import { PublicShell } from "@/components/shell/shell";
import { landingMessages } from "@/content/en/landing";
import { publicShellMessages } from "@/content/en/shell";
import { createDateFormatter } from "@/lib/format/date";

// Until locale routing (FE-050) exists the site serves English at `/`. Links to routes that later
// tasks build resolve to the safe not-found page meanwhile.
const links = {
  home: "/",
  localities: "/localities",
  report: "/report",
  sources: "/trust#sources",
  trust: "/trust"
} as const;

export default function LandingPage(): ReactNode {
  return (
    <PublicShell
      currentLocale="en"
      links={links}
      localeRoutes={{ en: "/" }}
      messages={publicShellMessages}
    >
      <FirstViewport
        browseHref="/projects"
        format={createDateFormatter("en")}
        messages={landingMessages}
        reportHref={links.report}
      />
    </PublicShell>
  );
}
