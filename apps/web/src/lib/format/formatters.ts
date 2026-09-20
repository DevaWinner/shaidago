import type { ApiLocale } from "@/lib/api/forwarded-context";

/**
 * Presentation-only formatters. They change how a stored value looks, never the value: amounts are
 * not converted between currencies or rounded away, instants are shown in `Africa/Lagos` without
 * changing the instant, and calendar dates never shift with a time zone. Nothing here parses a
 * formatted string back into domain data. A date that cannot be formatted is returned as given, and
 * an amount that is not a plain decimal is rejected, so a wrong value is never invented.
 */

const BCP47: Readonly<Record<ApiLocale, string>> = {
  en: "en-NG",
  ha: "ha-NG",
  ig: "ig-NG",
  yo: "yo-NG"
};

const PUBLIC_TIME_ZONE = "Africa/Lagos";
const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;
const DECIMAL = /^-?\d{1,15}(?:\.\d+)?$/;
const NAIRA_AMOUNT = /^-?\d{1,15}(?:\.\d{1,2})?$/;

const SECOND = 1000;
const MINUTE = 60 * SECOND;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

export type RelativeWithExact = Readonly<{
  /** e.g. "3 days ago". Always shown together with `exact`; the exact value is authoritative. */
  relative: string;
  exact: string;
}>;

export type Formatters = Readonly<{
  date: (isoValue: string) => string;
  dateTime: (isoValue: string) => string;
  relativeWithExact: (isoValue: string, now: Date) => RelativeWithExact | undefined;
  number: (value: number | string) => string;
  naira: (amount: number | string) => string;
  list: (items: readonly string[]) => string;
  languageName: (code: string) => string;
}>;

function decimalString(value: number | string, pattern: RegExp, what: string): string {
  const text = typeof value === "number" ? String(value) : value;

  // `String(1e21)` and non-finite numbers do not match, so they are rejected rather than guessed at.
  if (!pattern.test(text)) {
    throw new RangeError(`${what} must be a plain decimal`);
  }

  return text;
}

function instantOf(isoValue: string): Date | undefined {
  const instant = new Date(isoValue);

  return Number.isNaN(instant.getTime()) ? undefined : instant;
}

/** Picks the coarsest unit that keeps the number small; the exact date is always shown beside it. */
function relativeParts(deltaMs: number): { value: number; unit: Intl.RelativeTimeFormatUnit } {
  const size = Math.abs(deltaMs);
  const sign = Math.sign(deltaMs);

  if (size < MINUTE) {
    return { value: sign * Math.floor(size / SECOND), unit: "second" };
  }
  if (size < HOUR) {
    return { value: sign * Math.floor(size / MINUTE), unit: "minute" };
  }
  if (size < DAY) {
    return { value: sign * Math.floor(size / HOUR), unit: "hour" };
  }
  if (size < 30 * DAY) {
    return { value: sign * Math.floor(size / DAY), unit: "day" };
  }
  if (size < 365 * DAY) {
    return { value: sign * Math.floor(size / (30 * DAY)), unit: "month" };
  }

  return { value: sign * Math.floor(size / (365 * DAY)), unit: "year" };
}

export function createFormatters(language: ApiLocale): Formatters {
  const tag = BCP47[language];
  const instantDate = new Intl.DateTimeFormat(tag, {
    dateStyle: "long",
    timeZone: PUBLIC_TIME_ZONE
  });
  // A calendar date has no time zone: formatting it in UTC keeps the day the record states.
  const calendarDate = new Intl.DateTimeFormat(tag, { dateStyle: "long", timeZone: "UTC" });
  const dateTime = new Intl.DateTimeFormat(tag, {
    dateStyle: "long",
    timeStyle: "short",
    timeZone: PUBLIC_TIME_ZONE
  });
  const relative = new Intl.RelativeTimeFormat(tag, { numeric: "auto" });
  const plain = new Intl.NumberFormat(tag);
  const currency = new Intl.NumberFormat(tag, {
    style: "currency",
    currency: "NGN",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
  const conjunction = new Intl.ListFormat(tag, { type: "conjunction" });
  const names = new Intl.DisplayNames([tag], { type: "language" });

  const date = (isoValue: string): string => {
    if (DATE_ONLY.test(isoValue)) {
      const day = instantOf(`${isoValue}T00:00:00Z`);

      return day === undefined ? isoValue : calendarDate.format(day);
    }

    const instant = instantOf(isoValue);

    return instant === undefined ? isoValue : instantDate.format(instant);
  };

  return {
    date,
    dateTime: (isoValue) => {
      const instant = DATE_ONLY.test(isoValue) ? undefined : instantOf(isoValue);

      // A date with no time has no clock reading to show, so it is shown as a date.
      return instant === undefined ? date(isoValue) : dateTime.format(instant);
    },
    relativeWithExact: (isoValue, now) => {
      const instant = DATE_ONLY.test(isoValue) ? undefined : instantOf(isoValue);

      if (instant === undefined) {
        return undefined;
      }

      const { value, unit } = relativeParts(instant.getTime() - now.getTime());

      return { relative: relative.format(value, unit), exact: dateTime.format(instant) };
    },
    // Intl.NumberFormat accepts a decimal string and keeps full precision (ES2023); the lib typing
    // still says `number`, hence the assertion. The pattern above proves the string is a decimal.
    number: (value) => plain.format(decimalString(value, DECIMAL, "number") as unknown as number),
    naira: (amount) =>
      currency.format(decimalString(amount, NAIRA_AMOUNT, "amount") as unknown as number),
    list: (items) => conjunction.format(items),
    languageName: (code) => {
      try {
        return names.of(code) ?? code;
      } catch {
        // An invalid tag is shown as given rather than replaced with a guess.
        return code;
      }
    }
  };
}
