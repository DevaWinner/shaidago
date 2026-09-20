import { getRequestConfig } from "next-intl/server";

import { DEFAULT_LOCALE, isSupportedLocale } from "@/i18n/routing";

// Message catalogues arrive with FE-051; until then components read typed content modules.
export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;

  return {
    locale: isSupportedLocale(requested) ? requested : DEFAULT_LOCALE,
    messages: {}
  };
});
