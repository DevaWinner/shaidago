import type { ReactNode } from "react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { PwaSupport } from "@/components/pwa/pwa-support";
import { PublicShell } from "@/components/shell/shell";
import { resolveDomain } from "@/i18n/catalogue";
import { localeHref, type RouteState } from "@/i18n/locale-href";
import { LOCALES, REVIEWED_LOCALES } from "@/i18n/routing";
import type { ApiLocale } from "@/lib/api/forwarded-context";

/**
 * The public page frame every locale route uses: shell copy, locale-prefixed links, language links
 * to the equivalent route, and an honest notice when a critical part of the page is the original.
 */
export function SiteShell({
  children,
  locale,
  route
}: Readonly<{ children: ReactNode; locale: ApiLocale; route?: RouteState }>): ReactNode {
  const shell = resolveDomain(locale, "shell");
  const evidence = resolveDomain(locale, "evidence");
  const language = resolveDomain(locale, "language");
  const offline = resolveDomain(locale, "offline");
  const base = `/${locale}`;

  return (
    <PublicShell
      currentLocale={locale}
      languageSwitch={{
        announce: language.messages.changed,
        announceLanguage: language.language,
        guard: language.messages.draft
      }}
      links={{
        home: base,
        localities: `${base}/projects`,
        report: `${base}/report`,
        sources: `${base}/trust#sources`,
        trust: `${base}/trust`
      }}
      localeRoutes={{
        en: localeHref("en", route),
        ha: localeHref("ha", route),
        ig: localeHref("ig", route),
        yo: localeHref("yo", route)
      }}
      messages={shell.messages.public}
      unreviewedLocales={LOCALES.filter((code) => !REVIEWED_LOCALES.includes(code))}
    >
      <div className="mb-4">
        <PwaSupport copy={offline.messages} language={offline.language} />
      </div>
      {shell.isOriginal || evidence.isOriginal ? (
        <div className="mb-6">
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        </div>
      ) : null}
      {children}
    </PublicShell>
  );
}
