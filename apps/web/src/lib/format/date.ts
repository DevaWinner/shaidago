import type { ApiLocale } from "@/lib/api/forwarded-context";

const BCP47: Readonly<Record<ApiLocale, string>> = {
  en: "en-NG",
  ha: "ha-NG",
  ig: "ig-NG",
  yo: "yo-NG"
};

/**
 * Renders a stored UTC value as a public date in Africa/Lagos. Only the presentation changes; the
 * instant is never altered. FE-052 extends this module with numbers and currency.
 */
export function createDateFormatter(locale: ApiLocale): (isoValue: string) => string {
  const formatter = new Intl.DateTimeFormat(BCP47[locale], {
    dateStyle: "long",
    timeZone: "Africa/Lagos"
  });

  return (isoValue) => {
    const instant = new Date(isoValue);

    return Number.isNaN(instant.getTime()) ? isoValue : formatter.format(instant);
  };
}
