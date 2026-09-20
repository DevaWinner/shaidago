import type { Metadata, Viewport } from "next";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import "../globals.css";

import { LOCALES, contentLocale, isSupportedLocale } from "@/i18n/routing";

export const metadata: Metadata = {
  applicationName: "ShaidaGo",
  title: {
    default: "ShaidaGo",
    template: "%s | ShaidaGo"
  },
  description: "Source-backed project records and safer next actions for Abuja communities.",
  formatDetection: {
    address: false,
    email: false,
    telephone: false
  }
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#F7F2E8",
  width: "device-width",
  initialScale: 1
};

export function generateStaticParams(): { locale: string }[] {
  return LOCALES.map((locale) => ({ locale }));
}

type LocaleLayoutProperties = Readonly<{
  children: ReactNode;
  params: Promise<{ locale: string }>;
}>;

/**
 * The root layout for every public page. `lang` is the language the text is actually written in:
 * a locale without reviewed copy serves the English original and says so, so a screen reader never
 * pronounces English as Hausa, Igbo, or Yoruba. An unsupported segment is 404'd by the pages, and
 * the proxy redirects it before it gets here.
 */
export default async function LocaleLayout({
  children,
  params
}: LocaleLayoutProperties): Promise<ReactNode> {
  const { locale } = await params;
  const supported = isSupportedLocale(locale);

  if (supported) {
    setRequestLocale(locale);
  }

  return (
    <html lang={supported ? contentLocale(locale) : "en"}>
      <body>{children}</body>
    </html>
  );
}
