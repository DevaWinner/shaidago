import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import type { Messages } from "@/i18n/catalogue";
import type { Locality } from "@/lib/api/public-data";
import {
  CATEGORIES,
  STATUSES,
  VERIFICATIONS,
  type DirectoryFilters
} from "@/lib/directory/filters";

/**
 * The search and filter form. It is a plain GET form to the results URL, so it works with no
 * JavaScript and produces a shareable link; submitting always starts again from the first page.
 */
export function DirectoryForm({
  copy,
  evidence,
  filters,
  localities,
  locale
}: Readonly<{
  copy: Messages["directory"];
  evidence: Messages["evidence"];
  filters: DirectoryFilters;
  localities: readonly Locality[];
  locale: string;
}>): ReactNode {
  const form = copy.form;

  return (
    <form
      // The fragment survives a GET submission, so the results are scrolled to and (with JavaScript) focused.
      action={`/${locale}/projects#results`}
      aria-label={form.label}
      className="grid gap-4 border-y border-border py-4"
      method="get"
      role="search"
    >
      <Field controlId="directory-q" description={form.searchHelp} label={form.searchLabel}>
        <Input
          autoComplete="off"
          defaultValue={filters.q ?? ""}
          enterKeyHint="search"
          maxLength={100}
          name="q"
          type="search"
        />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Field controlId="directory-locality" label={form.locality}>
          <Select defaultValue={filters.locality ?? ""} name="locality">
            <option value="">{form.any}</option>
            {localities
              .filter((item) => item.kind === "area_council")
              .map((item) => (
                <option key={item.slug} value={item.slug}>
                  {item.name}
                </option>
              ))}
          </Select>
        </Field>
        <Field controlId="directory-category" label={form.category}>
          <Select defaultValue={filters.category ?? ""} name="category">
            <option value="">{form.any}</option>
            {CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {copy.categories[value]}
              </option>
            ))}
          </Select>
        </Field>
        <Field controlId="directory-status" label={form.status}>
          <Select defaultValue={filters.status ?? ""} name="status">
            <option value="">{form.any}</option>
            {STATUSES.map((value) => (
              <option key={value} value={value}>
                {copy.statuses[value]}
              </option>
            ))}
          </Select>
        </Field>
        <Field controlId="directory-verification" label={form.verification}>
          <Select defaultValue={filters.verification ?? ""} name="verification">
            <option value="">{form.any}</option>
            {VERIFICATIONS.map((value) => (
              <option key={value} value={value}>
                {evidence.verification[value]}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <div>
        {/* Submits the form natively; not a script-driven button. */}
        <Button type="submit">{form.apply}</Button>
      </div>
    </form>
  );
}
