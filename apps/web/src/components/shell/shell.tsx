import type { ReactNode } from "react";
import {
  BookOpenText,
  Check,
  ChevronDown,
  ClipboardList,
  FilePenLine,
  Languages,
  ListChecks,
  LogIn,
  SearchCheck
} from "lucide-react";

import { LanguageAnnouncer } from "@/components/shell/language-announcer";
import { LanguageLink, type DraftGuardCopy } from "@/components/shell/language-link";
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
  navReviewer: string;
  navTrack: string;
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
  reviewer: string;
  sources: string;
  track: string;
  trust: string;
}>;

export type PublicDestination = "home" | "localities" | "report" | "reviewer" | "track" | "trust";

const navList = "m-0 flex list-none flex-wrap items-center gap-x-2 gap-y-1 p-0";
const navLink =
  "inline-flex min-h-11 max-w-full min-w-0 items-center gap-2 rounded-ledger-control px-3 py-2 font-semibold text-foreground whitespace-normal no-underline [overflow-wrap:anywhere] hover:bg-[var(--state-selected-background)]";
const skipLink =
  "absolute start-2 top-2 z-10 -translate-y-[200%] bg-foreground px-4 py-3 font-bold text-background focus:translate-y-0";
const headerClasses = "border-b border-border bg-card";
const brandClasses =
  "inline-flex min-h-11 max-w-full flex-wrap items-center gap-3 text-ledger-lg font-extrabold text-foreground no-underline";
const mainClasses =
  "mx-auto box-border w-full max-w-[var(--layout-content-max)] px-[var(--layout-gutter)] py-8 focus:outline-none sm:py-10 lg:py-12";

const LOCALES: readonly ApiLocale[] = ["en", "ha", "ig", "yo"];

export type LanguageSwitch = Readonly<{
  /** Copy for the "you have an unsaved draft" confirmation. */
  guard: DraftGuardCopy;
  /** The announcement template with a `{language}` variable, and the language it is written in. */
  announce: string;
  announceLanguage: ApiLocale;
}>;

export type LocaleControlProperties = Readonly<{
  /** Locales whose reviewed content exists, with their route; others are shown as unavailable. */
  available: Readonly<Partial<Record<ApiLocale, string>>>;
  current: ApiLocale;
  messages: PublicShellMessages;
  /** Locales that have routes but no reviewed copy yet; each is labelled as such beside its link. */
  unreviewed?: readonly ApiLocale[];
  /** With this, links warn before discarding an unsaved draft and mark the switch for announcement. */
  languageSwitch?: LanguageSwitch | undefined;
}>;

/** A compact no-script dropdown. Each choice remains a real link and keeps draft protection. */
export function LocaleControl({
  available,
  current,
  messages,
  unreviewed = [],
  languageSwitch
}: LocaleControlProperties): ReactNode {
  return (
    <details className="group relative" data-slot="locale-control">
      <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 rounded-ledger-control border border-input bg-card px-3 py-2 font-semibold marker:hidden hover:bg-[var(--state-selected-background)] [&::-webkit-details-marker]:hidden">
        <Languages aria-hidden="true" className="size-5" strokeWidth={1.8} />
        <span>{messages.localeNames[current]}</span>
        <ChevronDown
          aria-hidden="true"
          className="size-4 transition-transform group-open:rotate-180"
        />
      </summary>
      <nav
        aria-label={messages.localeLabel}
        className="absolute end-0 top-[calc(100%+0.5rem)] z-30 w-[min(14rem,calc(100vw-2rem))] rounded-ledger-notice border border-input bg-card p-2 shadow-ledger-overlay"
      >
        <ul className="m-0 grid list-none gap-1 p-0">
          {LOCALES.map((locale) => {
            const href = available[locale];
            const name = messages.localeNames[locale];
            const note = unreviewed.includes(locale) ? (
              <span className="ms-1 text-muted-foreground" lang="en">
                ({messages.localeUnavailable})
              </span>
            ) : null;

            return (
              <li className="grid" key={locale}>
                {locale === current ? (
                  <span
                    aria-current="true"
                    className={cn(
                      navLink,
                      "justify-between bg-[var(--state-selected-background)] text-[var(--state-selected-text)]"
                    )}
                    lang={locale}
                  >
                    <span>
                      {name} <span className="sr-only">({messages.localeCurrentSuffix})</span>
                    </span>
                    <Check aria-hidden="true" className="size-4" />
                  </span>
                ) : href === undefined ? (
                  <span
                    aria-disabled="true"
                    className={cn(navLink, "font-normal text-muted-foreground")}
                    lang={locale}
                  >
                    {name} <span className="ms-1">({messages.localeUnavailable})</span>
                  </span>
                ) : languageSwitch === undefined ? (
                  <a className={navLink} href={href} hrefLang={locale} lang={locale}>
                    {name}
                  </a>
                ) : (
                  <LanguageLink
                    className={navLink}
                    guard={languageSwitch.guard}
                    href={href}
                    lang={locale}
                    language={locale}
                  >
                    {name}
                  </LanguageLink>
                )}
                {note}
              </li>
            );
          })}
        </ul>
      </nav>
    </details>
  );
}

export function PublicShell({
  active,
  children,
  currentLocale,
  lowDataControl,
  links,
  localeRoutes,
  messages,
  unreviewedLocales = [],
  languageSwitch
}: Readonly<{
  active?: PublicDestination;
  children: ReactNode;
  currentLocale: ApiLocale;
  /** Reserved for the low-data control; absent means nothing is rendered rather than a dead control. */
  lowDataControl?: ReactNode;
  links: PublicShellLinks;
  localeRoutes: LocaleControlProperties["available"];
  messages: PublicShellMessages;
  unreviewedLocales?: readonly ApiLocale[];
  languageSwitch?: LanguageSwitch;
}>): ReactNode {
  return (
    <div className="grid min-h-dvh grid-rows-[auto_auto_1fr_auto]" data-slot="shell">
      <a className={skipLink} href="#main-content">
        {messages.skipToContent}
      </a>
      <header className={headerClasses}>
        <div className="mx-auto grid w-full max-w-[var(--layout-content-max)] gap-2 px-[var(--layout-gutter)] py-3">
          <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
            <a
              aria-current={active === "home" ? "page" : undefined}
              className={brandClasses}
              href={links.home}
            >
              <span className="grid size-9 place-items-center rounded-ledger-control bg-primary text-primary-foreground">
                <SearchCheck aria-hidden="true" className="size-5" strokeWidth={1.8} />
              </span>
              {messages.productName}
            </a>
            <div className="ms-auto flex max-w-full items-center gap-1 sm:gap-2">
              <a
                aria-current={active === "track" ? "page" : undefined}
                className={cn(
                  navLink,
                  "hidden sm:inline-flex",
                  active === "track" && "bg-[var(--state-selected-background)]"
                )}
                href={links.track}
              >
                <ClipboardList aria-hidden="true" className="size-4" />
                {messages.navTrack}
              </a>
              <a
                aria-current={active === "reviewer" ? "page" : undefined}
                className={cn(
                  navLink,
                  "hidden lg:inline-flex",
                  active === "reviewer" && "bg-[var(--state-selected-background)]"
                )}
                href={links.reviewer}
              >
                <LogIn aria-hidden="true" className="size-4" />
                {messages.navReviewer}
              </a>
              <LocaleControl
                available={localeRoutes}
                current={currentLocale}
                messages={messages}
                languageSwitch={languageSwitch}
                unreviewed={unreviewedLocales}
              />
            </div>
          </div>
          <nav aria-label={messages.navLabel} className="border-t border-border pt-2">
            <ul className={navList}>
              <li>
                <a
                  aria-current={active === "localities" ? "page" : undefined}
                  className={cn(
                    navLink,
                    active === "localities" && "bg-[var(--state-selected-background)]"
                  )}
                  href={links.localities}
                >
                  <BookOpenText aria-hidden="true" className="size-4" />
                  {messages.navLocalities}
                </a>
              </li>
              <li>
                <a
                  aria-current={active === "trust" ? "page" : undefined}
                  className={cn(
                    navLink,
                    active === "trust" && "bg-[var(--state-selected-background)]"
                  )}
                  href={links.trust}
                >
                  <ListChecks aria-hidden="true" className="size-4" />
                  {messages.navTrust}
                </a>
              </li>
              <li>
                <a
                  aria-current={active === "report" ? "page" : undefined}
                  className="inline-flex min-h-11 items-center gap-2 rounded-ledger-control bg-primary px-4 py-2 font-semibold text-primary-foreground no-underline hover:bg-ledger-accent-strong"
                  href={links.report}
                >
                  <FilePenLine aria-hidden="true" className="size-4" />
                  {messages.navReport}
                </a>
              </li>
              <li className="sm:hidden">
                <a
                  aria-current={active === "track" ? "page" : undefined}
                  className={cn(
                    navLink,
                    active === "track" && "bg-[var(--state-selected-background)]"
                  )}
                  href={links.track}
                >
                  <ClipboardList aria-hidden="true" className="size-4" />
                  {messages.navTrack}
                </a>
              </li>
              <li className="lg:hidden">
                <a
                  aria-current={active === "reviewer" ? "page" : undefined}
                  className={cn(
                    navLink,
                    active === "reviewer" && "bg-[var(--state-selected-background)]"
                  )}
                  href={links.reviewer}
                >
                  <LogIn aria-hidden="true" className="size-4" />
                  {messages.navReviewer}
                </a>
              </li>
            </ul>
          </nav>
          {lowDataControl}
        </div>
      </header>
      {/* Reserved for offline and stale notices; it announces politely and is empty by default. */}
      <div
        aria-label={messages.statusRegionLabel}
        aria-live="polite"
        className="border-b border-border px-[var(--layout-gutter)] py-2 empty:hidden"
        data-slot="shell-status"
        role="status"
      >
        {languageSwitch === undefined ? null : (
          <LanguageAnnouncer
            current={currentLocale}
            language={languageSwitch.announceLanguage}
            languageName={messages.localeNames[currentLocale]}
            template={languageSwitch.announce}
          />
        )}
      </div>
      <main className={mainClasses} id="main-content" tabIndex={-1}>
        {children}
      </main>
      <footer
        aria-label={messages.footerLabel}
        className="border-t border-border bg-card px-[var(--layout-gutter)] pb-8 pt-6 text-muted-foreground"
        data-slot="shell-footer"
      >
        <div className="mx-auto grid w-full max-w-[var(--layout-content-max)] gap-4 md:grid-cols-[1fr_auto]">
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
            <li>
              <a className={navLink} href={links.track}>
                {messages.navTrack}
              </a>
            </li>
            <li>
              <a className={navLink} href={links.reviewer}>
                {messages.navReviewer}
              </a>
            </li>
          </ul>
          <p className="m-0 max-w-[68ch]">{messages.notEmergency}</p>
        </div>
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
        <div className="mx-auto flex w-full max-w-[var(--layout-content-max)] flex-wrap items-center gap-3 px-[var(--layout-gutter)] py-3">
          <a className={brandClasses} href={homeHref}>
            <span className="grid size-9 place-items-center rounded-ledger-control bg-primary text-primary-foreground">
              <SearchCheck aria-hidden="true" className="size-5" strokeWidth={1.8} />
            </span>
            {messages.productName}{" "}
            <span className="border border-border px-2 text-sm font-bold" data-slot="shell-area">
              {messages.area}
            </span>
          </a>
          <nav aria-label={messages.navLabel} className="ms-auto">
            <ul className={navList}>
              <li>
                <a className={navLink} href={queueHref}>
                  <ClipboardList aria-hidden="true" className="size-4" />
                  {messages.queue}
                </a>
              </li>
            </ul>
          </nav>
          {sessionControl}
        </div>
      </header>
      <main className={mainClasses} id="main-content" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
