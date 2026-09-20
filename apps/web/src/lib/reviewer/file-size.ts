import type { Formatters } from "@/lib/format/formatters";

type Units = Readonly<{ bytes: string; kilobytes: string; megabytes: string }>;

const KILOBYTE = 1024;
const MEGABYTE = 1024 * 1024;

const tenth = (value: number): string => String(Math.round(value * 10) / 10);

/** A file size in the largest whole unit, with the exact byte count kept for small files. */
export function describeSize(
  bytes: number,
  units: Units,
  format: Pick<Formatters, "number">,
  plural: (template: string, count: number) => string
): string {
  if (bytes < KILOBYTE) {
    return plural(units.bytes, bytes);
  }
  if (bytes < MEGABYTE) {
    return units.kilobytes.replace("{count}", format.number(tenth(bytes / KILOBYTE)));
  }

  return units.megabytes.replace("{count}", format.number(tenth(bytes / MEGABYTE)));
}
