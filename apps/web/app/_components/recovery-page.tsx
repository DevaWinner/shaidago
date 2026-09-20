import type { ReactNode } from "react";

type RecoveryPageProperties = Readonly<{
  title: string;
  children: ReactNode;
  /** The full, already-localised line, e.g. "Support reference: <id>". */
  referenceText?: string | undefined;
  action?: ReactNode | undefined;
}>;

export function RecoveryPage({
  title,
  children,
  referenceText,
  action
}: RecoveryPageProperties): ReactNode {
  return (
    <main aria-labelledby="recovery-title">
      <h1 id="recovery-title">{title}</h1>
      <p>{children}</p>
      {referenceText ? <p>{referenceText}</p> : null}
      {action}
    </main>
  );
}
