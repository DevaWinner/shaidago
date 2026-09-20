import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";
import { FilePenLine } from "lucide-react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { PageState } from "@/components/project/page-state";
import { ReportWizard } from "@/components/report/report-wizard";
import { SiteShell } from "@/components/shell/site-shell";
import { PageHeader } from "@/components/ui/page-header";
import { resolveDomain } from "@/i18n/catalogue";
import { isSupportedLocale } from "@/i18n/routing";
import { loadProject } from "@/lib/api/public-data";
import { isProjectSlug } from "@/lib/identifiers";

// Never cached or indexed: the form is per visitor and holds private input once they type.
export const dynamic = "force-dynamic";

type Properties = Readonly<{ params: Promise<{ locale: string; slug: string }> }>;

export async function generateMetadata({ params }: Properties): Promise<Metadata> {
  const { locale } = await params;

  return {
    title: isSupportedLocale(locale) ? resolveDomain(locale, "report").messages.title : undefined,
    robots: { index: false, follow: false, nocache: true }
  };
}

export default async function ReportPage({ params }: Properties): Promise<ReactNode> {
  const { locale, slug } = await params;

  if (!isSupportedLocale(locale) || !isProjectSlug(slug)) {
    notFound();
  }

  setRequestLocale(locale);
  const report = resolveDomain(locale, "report");
  const evidence = resolveDomain(locale, "evidence");
  const problems = resolveDomain(locale, "problems");
  const project = await loadProject(slug, locale);

  if (project.state === "not_found" || project.state === "invalid_cursor") {
    notFound();
  }

  const route = { segments: ["report", slug] } as const;

  if (project.state === "unavailable") {
    return (
      <SiteShell locale={locale} route={route}>
        <div lang={report.language}>
          <PageState
            actionHref={`/${locale}/report/${encodeURIComponent(slug)}`}
            actionLabel={report.messages.chooser.browse}
            body={report.messages.unknownProject.body}
            title={report.messages.unknownProject.title}
          />
        </div>
      </SiteShell>
    );
  }

  return (
    <SiteShell locale={locale} route={route}>
      <div className="grid gap-6" lang={report.language}>
        {report.isOriginal || problems.isOriginal ? (
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        ) : null}
        <PageHeader icon={FilePenLine} title={report.messages.title} />
        <ReportWizard
          copy={report.messages}
          handleHref={`/${locale}/handle`}
          language={report.language}
          locale={locale}
          problems={problems.messages}
          projectTitle={project.data.text.title}
          slug={slug}
          trustHref={`/${locale}/trust`}
        />
      </div>
    </SiteShell>
  );
}
