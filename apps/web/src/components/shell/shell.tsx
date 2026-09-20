import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import type { ApiLocale } from "@/lib/api/forwarded-context";

/**
 * Application shells. Every string arrives as a typed message record, links are plain anchors so
 * the shell works without JavaScript, and the public shell hides nothing behind a menu: its few
 * items wrap on a narrow screen, so there is no hidden navigation to trap focus in.
 */

export type LocaleName = Readonly<Record<ApiLocale, string>>;

export type PublicShellMessages = Readonly<{
  footerLabel: string;
  footerSources: string;
  footerTrust: string;
  localeCurrentSuffix: string;
  localeLabel: string;
  localeNames: LocaleName;
  localeUnavailable: string;
  navLabel: string;
  navLocalities: string;
  navReport: string;
  navTrust: string;
  notEmergency: string;
  productName: string;
  skipToContent: string;
  statusRegionLabel: string;
}>;

export type PublicShellLinks = Readonly<{
  home: string;
  localities: string;
  report: string;
  sources: string;
  trust: string;
}>;

const navList = "m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0";
const navLink =
  "inline-flex min-h-11 items-center font-semibold text-ledger-accent-strong [overflow-wrap:anywhere]";
const skipLink =
  "absolute start-2 top-2 z-10 -translate-y-[200%] bg-foreground px-4 py-3 font-bold text-background focus:translate-y-0";
const headerClasses =
  "flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-border px-[var(--layout-gutter)] py-3";
const brandClasses =
  "inline-flex min-h-11 items-center gap-2 text-ledger-lg font-extrabold text-foreground no-underline";
const mainClasses =
  "mx-auto box-border w-full max-w-[var(--layout-content-max)] px-[var(--layout-gutter)] py-8 focus:outline-none";

const LOCALES: readonly ApiLocale[] = ["en", "ha", "ig", "yo"];

export type LocaleControlProperties = Readonly<{
  /** Locales whose reviewed content exists, with their route; others are shown as unavailable. */
  available: Readonly<Partial<Record<ApiLocale, string>>>;
  current: ApiLocale;
  messages: PublicShellMessages;
  /** Locales that have routes but no reviewed copy yet; each is labelled as such beside its link. */
  unreviewed?: readonly ApiLocale[];
}>;

/** A list of links, not a script-driven select: it works with no JavaScript and is fully labelled. */
export function LocaleControl({
  available,
  current,
  messages,
  unreviewed = []
}: LocaleControlProperties): ReactNode {
  return (
    <nav aria-label={messages.localeLabel} className="ms-auto" data-slot="locale-control">
      <ul className={navList}>
        {LOCALES.map((locale) => {
          const href = available[locale];
          const name = messages.localeNames[locale];
          const note = unreviewed.includes(locale) ? (
            <span className="ms-1 text-muted-foreground" lang="en">
              ({messages.localeUnavailable})
            </span>
          ) : null;

          return (
            <li className="inline-flex items-center" key={locale}>
              {locale === current ? (
                <span
                  aria-current="true"
                  className={cn(navLink, "border-b-2 border-primary text-foreground")}
                  lang={locale}
                >
                  {name} <span className="sr-only">({messages.localeCurrentSuffix})</span>
                </span>
              ) : href === undefined ? (
                <span
                  aria-disabled="true"
                  className={cn(navLink, "font-normal text-muted-foreground")}
                  lang={locale}
                >
                  {name} <span className="ms-1">({messages.localeUnavailable})</span>
                </span>
              ) : (
                <a className={navLink} href={href} hrefLang={locale} lang={locale}>
                  {name}
                </a>
              )}
              {note}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function PublicShell({
  children,
  currentLocale,
  lowDataControl,
  links,
  localeRoutes,
  messages,
  unreviewedLocales = []
}: Readonly<{
  children: ReactNode;
  currentLocale: ApiLocale;
  /** Reserved for the low-data control; absent means nothing is rendered rather than a dead control. */
  lowDataControl?: ReactNode;
  links: PublicShellLinks;
  localeRoutes: LocaleControlProperties["available"];
  messages: PublicShellMessages;
  unreviewedLocales?: readonly ApiLocale[];
}>): ReactNode {
  return (
    <div className="grid min-h-dvh grid-rows-[auto_auto_1fr_auto]" data-slot="shell">
      <a className={skipLink} href="#main-content">
        {messages.skipToContent}
      </a>
      <header className={headerClasses}>
        <a className={brandClasses} href={links.home}>
          {messages.productName}
        </a>
        <nav aria-label={messages.navLabel}>
          <ul className={navList}>
            <li>
              <a className={navLink} href={links.localities}>
                {messages.navLocalities}
              </a>
            </li>
            <li>
              <a className={navLink} href={links.trust}>
                {messages.navTrust}
              </a>
            </li>
            <li>
              <a className={cn(navLink, "text-foreground")} href={links.report}>
                {messages.navReport}
              </a>
            </li>
          </ul>
        </nav>
        <LocaleControl
          available={localeRoutes}
          current={currentLocale}
          messages={messages}
          unreviewed={unreviewedLocales}
        />
        {lowDataControl}
      </header>
      {/* Reserved for offline and stale notices; it announces politely and is empty by default. */}
      <div
        aria-label={messages.statusRegionLabel}
        aria-live="polite"
        className="border-b border-border px-[var(--layout-gutter)] py-2 empty:hidden"
        data-slot="shell-status"
        role="status"
      />
      <main className={mainClasses} id="main-content" tabIndex={-1}>
        {children}
      </main>
      <footer
        aria-label={messages.footerLabel}
        className="grid gap-2 border-t border-border px-[var(--layout-gutter)] pb-8 pt-4 text-muted-foreground"
        data-slot="shell-footer"
      >
        <ul className={navList}>
          <li>
            <a className={navLink} href={links.trust}>
              {messages.footerTrust}
            </a>
          </li>
          <li>
            <a className={navLink} href={links.sources}>
              {messages.footerSources}
            </a>
          </li>
        </ul>
        <p className="m-0 max-w-[68ch]">{messages.notEmergency}</p>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------

export type ReviewerShellMessages = Readonly<{
  area: string;
  navLabel: string;
  productName: string;
  queue: string;
  skipToContent: string;
}>;

/**
 * The reviewer frame. Links are plain anchors on purpose: the framework's link component
 * prefetches, and a prefetch of a private route would request private data no one asked to see.
 * Routes that use this shell must also be dynamic and `no-store`; that is their responsibility.
 */
export function ReviewerShell({
  children,
  homeHref,
  messages,
  queueHref,
  sessionControl
}: Readonly<{
  children: ReactNode;
  homeHref: string;
  messages: ReviewerShellMessages;
  queueHref: string;
  /** The sign-out control, supplied by the page so this shell stays server-rendered. */
  sessionControl: ReactNode;
}>): ReactNode {
  return (
    <div className="grid min-h-dvh grid-rows-[auto_1fr]" data-shell="reviewer" data-slot="shell">
      <a className={skipLink} href="#main-content">
        {messages.skipToContent}
      </a>
      <header className={cn(headerClasses, "border-b-[6px] border-double")}>
        <a className={brandClasses} href={homeHref}>
          {messages.productName}{" "}
          <span className="border border-border px-2 text-sm font-bold" data-slot="shell-area">
            {messages.area}
          </span>
        </a>
        <nav aria-label={messages.navLabel}>
          <ul className={navList}>
            <li>
              <a className={navLink} href={queueHref}>
                {messages.queue}
              </a>
            </li>
          </ul>
        </nav>
        {sessionControl}
      </header>
      <main className={mainClasses} id="main-content" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
