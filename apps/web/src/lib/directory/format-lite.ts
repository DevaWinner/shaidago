/**
 * Substitutes simple `{name}` variables. It is used only for catalogue strings whose sole ICU
 * feature is a plain argument (the parity check guarantees the variable names match English), so
 * server-rendered components need no ICU runtime. Plural strings go through `formatMessage`.
 */
export function formatMessageLite(
  template: string,
  values: Readonly<Record<string, string | number>>
): string {
  return Object.entries(values).reduce(
    (text, [name, value]) => text.split(`{${name}}`).join(String(value)),
    template
  );
}
